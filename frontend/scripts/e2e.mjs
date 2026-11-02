#!/usr/bin/env node
/**
 * UI 回归：一条命令走完关键路径。
 *
 * 为什么需要它：后端有 journey / smoke 两套断言，但"点得对不对"一直靠临时写的
 * CDP 脚本，跑完就丢——下次改前端还得从零写一遍，成本高且容易漏。
 * 这里把最容易回归的几条路径固化下来：首页、搜索四页签、发帖结果面板、
 * 大图预览、通知、个人中心「我赞过的」。
 *
 * 用法（前后端都要先起来）：
 *   cd frontend && npm run e2e
 *
 * 依赖：本机 Chrome（或用 CHROME_PATH 指定）、Node 18+（自带 fetch / WebSocket）。
 * 跑完会删掉自己发的测试帖；为保证不污染菜品均分，发帖时选的是"该用户已评过
 * 且分数相同"的菜，覆盖后聚合值不变。
 */
import { spawn } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

const API = process.env.E2E_API ?? 'http://127.0.0.1:8000/api/v1'
const WEB = process.env.E2E_WEB ?? 'http://127.0.0.1:5173'
const STUDENT = { username: process.env.E2E_USER ?? 'xiaoming', password: process.env.E2E_PASSWORD ?? '123456' }
const ADMIN = { username: process.env.E2E_ADMIN ?? 'admin', password: process.env.E2E_ADMIN_PASSWORD ?? 'admin123' }
const OUT = path.join(process.cwd(), '.e2e-shots')

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
let pass = 0
let failed = 0

function ok(name, cond, detail) {
  if (cond) {
    pass += 1
    console.log(`  ok    ${name}`)
  } else {
    failed += 1
    const extra = detail === undefined ? '' : `  → ${JSON.stringify(detail).slice(0, 240)}`
    console.log(`  FAIL  ${name}${extra}`)
  }
}

async function api(method, p, body, token) {
  const res = await fetch(`${API}${p}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  })
  return res.json()
}

function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    process.env.LOCALAPPDATA && path.join(process.env.LOCALAPPDATA, 'Google/Chrome/Application/chrome.exe'),
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ].filter(Boolean)
  return candidates.find((p) => fs.existsSync(p))
}

async function waitServices() {
  for (let i = 0; i < 20; i += 1) {
    try {
      const [b, w] = await Promise.all([fetch(`${API}/canteens`), fetch(WEB)])
      if (b.ok && w.ok) return true
    } catch {
      // 还没起来，继续等
    }
    await sleep(500)
  }
  return false
}

/** 极简 CDP 客户端，够用即可，不引 puppeteer */
class Tab {
  constructor(ws) {
    this.ws = ws
    this.id = 0
    this.pending = new Map()
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id)
        this.pending.delete(msg.id)
        msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result)
      }
    }
  }

  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = (this.id += 1)
      this.pending.set(id, { resolve, reject })
      this.ws.send(JSON.stringify({ id, method, params }))
    })
  }

  async eval(expression) {
    const r = await this.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text)
    return r.result.value
  }

  async goto(url) {
    await this.send('Page.navigate', { url })
    await sleep(600)
  }

  /** 轮询等待页面条件成立，比固定 sleep 稳 */
  async waitFor(expression, timeout = 8000) {
    const deadline = Date.now() + timeout
    while (Date.now() < deadline) {
      try {
        if (await this.eval(expression)) return true
      } catch {
        // 页面切换期间 evaluate 可能失败，重试即可
      }
      await sleep(200)
    }
    return false
  }

  async shot(name) {
    fs.mkdirSync(OUT, { recursive: true })
    const { data } = await this.send('Page.captureScreenshot', { format: 'png' })
    fs.writeFileSync(path.join(OUT, name), Buffer.from(data, 'base64'))
    console.log(`  ·     截图 ${path.join('.e2e-shots', name)}`)
  }

  async key(keyName) {
    const map = { Escape: 27 }
    const code = map[keyName]
    await this.send('Input.dispatchKeyEvent', { type: 'keyDown', windowsVirtualKeyCode: code, key: keyName })
    await this.send('Input.dispatchKeyEvent', { type: 'keyUp', windowsVirtualKeyCode: code, key: keyName })
  }
}

async function main() {
  if (!(await waitServices())) {
    console.error(`\n前后端没起来。先跑：\n  cd backend && ./.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000\n  cd frontend && npm run dev\n`)
    process.exit(2)
  }

  const chromePath = findChrome()
  if (!chromePath) {
    console.error('找不到 Chrome，可用 CHROME_PATH 指定可执行文件路径。')
    process.exit(2)
  }

  const login = await api('POST', '/auth/login', STUDENT)
  if (login.code !== 0) {
    console.error('学生账号登录失败：', login.message)
    process.exit(2)
  }
  const token = login.data.access_token
  const adminToken = (await api('POST', '/auth/login', ADMIN)).data?.access_token

  // 选一道"我已经评过"的菜：发帖时用同样的分数，菜品聚合不会被测试数据带偏
  const ratings = await api('GET', `/users/${login.data.user.id}/ratings?page_size=1`, null, token)
  const rated = ratings.data?.items?.[0]
  if (!rated) {
    console.error('该账号还没有任何评价记录，无法在不污染聚合的前提下测试发帖。')
    process.exit(2)
  }

  const port = 9400 + Math.floor(Math.random() * 90)
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'campus-e2e-'))
  const chrome = spawn(chromePath, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    '--no-first-run',
    '--disable-gpu',
    '--hide-scrollbars',
  ], { stdio: 'ignore' })

  let ws
  let createdPostId = null
  try {
    let target = null
    for (let i = 0; i < 60; i += 1) {
      try {
        target = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json()
        break
      } catch {
        await sleep(250)
      }
    }
    if (!target) throw new Error('连不上 Chrome 的调试端口')

    ws = new WebSocket(target.webSocketDebuggerUrl)
    await new Promise((resolve, reject) => {
      ws.onopen = resolve
      ws.onerror = reject
    })
    const tab = new Tab(ws)
    await tab.send('Page.enable')
    await tab.send('Runtime.enable')
    await tab.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false })

    // ---------------------------------------------------------------- 首页
    console.log('\n== 首页')
    await tab.goto(WEB + '/')
    await tab.eval(`localStorage.setItem('cf_token', ${JSON.stringify(token)})`)
    await tab.goto(WEB + '/')
    await tab.waitFor(`document.querySelectorAll('.postcard').length > 0 || !!document.querySelector('.empty')`)
    const cards = await tab.eval(`document.querySelectorAll('.postcard').length`)
    ok('首页渲染出帖子卡片', cards > 0, cards)
    ok('首页没有错误态', !(await tab.eval(`!!document.querySelector('[class*="error"]')`)))
    ok('顶栏铃铛可见', await tab.eval(`!!document.querySelector('.bell')`))

    // ---------------------------------------------------------------- 关注流
    console.log('== 关注流')
    await tab.eval(`Array.from(document.querySelectorAll('.tab')).find(e => e.innerText.includes('关注'))?.click()`)
    await sleep(1200)
    const followState = await tab.eval(`({
      posts: document.querySelectorAll('.postcard').length,
      empty: !!document.querySelector('.empty'),
      t: document.body.innerText.includes('还没关注任何人') || document.body.innerText.includes('发帖后会出现在这里')
    })`)
    ok('关注 tab 有内容或给出空态引导', followState.posts > 0 || followState.empty || followState.t, followState)

    // ---------------------------------------------------------------- 搜索
    console.log('== 搜索')
    await tab.goto(WEB + '/search?kw=' + encodeURIComponent('拉面'))
    await tab.waitFor(`document.querySelectorAll('.el-tabs__item').length >= 4`)
    const tabs = await tab.eval(`Array.from(document.querySelectorAll('.el-tabs__item')).map(e => e.innerText.trim()).join('|')`)
    ok('搜索有四个页签', ['菜品', '帖子', '商家', '用户'].every((k) => tabs.includes(k)), tabs)

    await tab.eval(`Array.from(document.querySelectorAll('.el-tabs__item')).find(e => e.innerText.includes('商家'))?.click()`)
    await sleep(600)
    ok('搜「拉面」在商家页签有结果', (await tab.eval(`document.querySelectorAll('.mark').length`)) > 0)

    await tab.goto(WEB + '/search?kw=' + encodeURIComponent('红红'))
    await tab.waitFor(`document.querySelector('.el-tabs__item.is-active')?.innerText.includes('用户')`)
    const activeTab = await tab.eval(`document.querySelector('.el-tabs__item.is-active')?.innerText.trim()`)
    ok('菜品无结果时自动落到用户页签', String(activeTab).includes('用户'), activeTab)
    ok('用户结果可直接关注', await tab.eval(`!!document.querySelector('.person .el-button')`))
    ok('排序/说明文案含粉丝数', String(await tab.eval(`document.querySelector('.person')?.innerText || ''`)).includes('粉丝'))

    // ---------------------------------------------------------------- 发帖 + 结果面板
    console.log('== 发帖结果面板')
    await tab.goto(`${WEB}/create?dish_id=${rated.dish.id}`)
    await tab.waitFor(`!!document.querySelector('.chosen')`)
    await tab.eval(`document.querySelectorAll('.el-rate__item')[${Math.max(0, rated.score - 1)}]?.click()`)
    await sleep(300)
    await tab.eval(`Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim() === '发布')?.click()`)
    const panelReady = await tab.waitFor(`!!document.querySelector('.done')`, 12000)
    ok('发布后出现结果面板', panelReady)
    if (panelReady) {
      const panel = await tab.eval(`document.querySelector('.done').innerText.replace(/\\n+/g, ' | ')`)
      ok('面板含菜名与「人评过」', String(panel).includes(rated.dish.name) && String(panel).includes('人评过'), panel)
      ok('面板含榜单位次或差距提示', /高分榜|再有|才能上榜/.test(String(panel)), panel)

      // 找出刚发的帖子，供后面清理
      const feed = await api('GET', '/posts/feed?sort=latest&page_size=5', null, token)
      const mine = feed.data.items.find((p) => p.author.id === login.data.user.id && p.dish.id === rated.dish.id)
      createdPostId = mine?.id ?? null

      await tab.eval(`Array.from(document.querySelectorAll('.done .el-button')).find(b => b.innerText.includes('看这道菜'))?.click()`)
      await tab.waitFor(`location.pathname.startsWith('/dishes/')`)
      ok('「看这道菜」跳到菜品页', (await tab.eval(`location.pathname`)).startsWith('/dishes/'))
    }

    // ---------------------------------------------------------------- 大图预览
    console.log('== 大图预览')
    const anyPost = await api('GET', '/posts/feed?sort=latest&page_size=10')
    const withImage = anyPost.data.items.find((p) => (p.images || []).length > 0) ?? anyPost.data.items[0]
    await tab.goto(`${WEB}/posts/${withImage.id}`)
    await tab.waitFor(`document.querySelectorAll('.thumbs.zoomable img').length > 0`)
    await tab.eval(`document.querySelector('.thumbs.zoomable img')?.click()`)
    await tab.waitFor(`!!document.querySelector('.viewer')`)
    ok('详情页点图打开大图', await tab.eval(`!!document.querySelector('.viewer')`))
    await tab.key('Escape')
    await sleep(400)
    ok('Esc 关闭大图', !(await tab.eval(`!!document.querySelector('.viewer')`)))

    // ---------------------------------------------------------------- 同店其他菜
    console.log('== 同店其他菜')
    // 找一家有 3 道以上在售菜的商家：只有菜品够多，才能同时验证"排除自己"和"排序"
    let siblingDish = null
    const canteens = await api('GET', '/canteens')
    for (const canteen of canteens.data || []) {
      const merchants = await api('GET', `/canteens/${canteen.id}/merchants`)
      for (const merchant of merchants.data || []) {
        const dishes = await api('GET', `/merchants/${merchant.id}/dishes`)
        if ((dishes.data || []).length >= 3) {
          siblingDish = dishes.data[0]
          break
        }
      }
      if (siblingDish) break
    }
    if (siblingDish) {
      await tab.goto(`${WEB}/dishes/${siblingDish.id}`)
      await tab.waitFor(`document.querySelectorAll('.sib').length > 0`, 8000)
      const sib = await tab.eval(`({
        count: document.querySelectorAll('.sib').length,
        names: Array.from(document.querySelectorAll('.sib-name')).map(e => e.innerText.trim()),
        scores: Array.from(document.querySelectorAll('.sib-score')).map(e => e.innerText.trim()),
      })`)
      ok('菜品页有「这家还有」', sib.count > 1, sib)
      ok('同店推荐不含当前这道', !sib.names.includes(siblingDish.name), { cur: siblingDish.name, names: sib.names })
      const nums = sib.scores.map((s) => Number.parseFloat(s) || 0)
      ok('同店推荐按均分倒序', nums.every((v, i) => i === 0 || nums[i - 1] >= v), nums)
    }

    // ---------------------------------------------------------------- 通知
    console.log('== 通知中心')
    await tab.goto(WEB + '/notifications')
    await tab.waitFor(`document.querySelectorAll('.row').length > 0 || !!document.querySelector('.empty')`, 10000)
    const notifyState = await tab.eval(`({ rows: document.querySelectorAll('.row').length, empty: !!document.querySelector('.empty') })`)
    ok('通知页有列表或空态', notifyState.rows > 0 || notifyState.empty, notifyState)

    // ---------------------------------------------------------------- 个人中心
    console.log('== 个人中心')
    await tab.goto(WEB + '/me')
    await tab.waitFor(`document.querySelectorAll('.el-tabs__item').length > 0`)
    const myTabs = await tab.eval(`Array.from(document.querySelectorAll('.el-tabs__item')).map(e => e.innerText.trim().replace(/\\s+/g,' ')).join('|')`)
    ok('有「我赞过的」页签', String(myTabs).includes('我赞过的'), myTabs)
    await tab.eval(`Array.from(document.querySelectorAll('.el-tabs__item')).find(e => e.innerText.includes('我赞过的'))?.click()`)
    // 页签容器一直在，等的是"数据到了"——卡片或空态出现才算加载完
    await tab.waitFor(
      `document.querySelectorAll('#pane-liked .postcard').length > 0 || !!document.querySelector('#pane-liked .empty')`,
      10000,
    )
    const likedState = await tab.eval(`({ cards: document.querySelectorAll('#pane-liked .postcard').length, empty: !!document.querySelector('#pane-liked .empty') })`)
    ok('「我赞过的」有卡片或空态', likedState.cards > 0 || likedState.empty, likedState)

    // 别人的主页不应出现这个页签
    const other = await api('GET', `/users?keyword=${encodeURIComponent('红红')}`)
    const otherId = other.data?.items?.[0]?.id
    if (otherId) {
      await tab.goto(`${WEB}/users/${otherId}`)
      await tab.waitFor(`document.querySelectorAll('.el-tabs__item').length > 0`)
      const otherTabs = await tab.eval(`Array.from(document.querySelectorAll('.el-tabs__item')).map(e => e.innerText).join('|')`)
      ok('别人的主页不显示「我赞过的」', !String(otherTabs).includes('我赞过的'), otherTabs)
    }

    // ---------------------------------------------------------------- 移动端
    console.log('== 移动端')
    await tab.send('Emulation.setDeviceMetricsOverride', { width: 375, height: 812, deviceScaleFactor: 2, mobile: true })
    await tab.goto(WEB + '/')
    await sleep(1200)
    ok('首页 375px 无横向溢出', !(await tab.eval(`document.documentElement.scrollWidth > window.innerWidth`)))
    await tab.goto(WEB + '/me')
    await sleep(1500)
    ok('个人中心 375px 无横向溢出', !(await tab.eval(`document.documentElement.scrollWidth > window.innerWidth`)))
  } catch (error) {
    failed += 1
    console.error('\n执行中断：', error.message)
    if (ws) {
      try {
        const tab = new Tab(ws)
        await tab.shot('crash.png')
      } catch {
        // 截图失败就算了
      }
    }
  } finally {
    if (ws) ws.close()
    chrome.kill()
    fs.rmSync(profile, { recursive: true, force: true })
    // 清理测试帖：不删会越积越多，也会让首页多一条"e2e"文案
    if (createdPostId && adminToken) {
      const del = await api('DELETE', `/admin/posts/${createdPostId}`, null, adminToken)
      console.log(`\n清理测试帖 #${createdPostId}：${del.code === 0 ? '已删除' : del.message}`)
    }
  }

  console.log(`\n通过 ${pass} / ${pass + failed}`)
  process.exit(failed ? 1 : 0)
}

main()
