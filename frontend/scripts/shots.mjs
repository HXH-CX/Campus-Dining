/**
 * 生成 README 用的界面截图。
 *
 * 为什么单独一个脚本而不是手动截：
 * 仓库里的截图必须能重放——改了样式要能一次重新生成全套，
 * 而不是靠人记住「哪几张图该重截」。和 e2e.mjs 一样走 CDP 驱动本机 Chrome，
 * 不引 puppeteer（为了几张图装一个 Chromium 不划算）。
 *
 * 前置：前端后端都在跑。
 *   cd backend  && .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
 *   cd frontend && npm run dev
 *
 * 登录：本脚本不碰密码。token 用下面这行本地生成（需要 backend 目录下执行）：
 *   .venv/Scripts/python.exe -c "from app.core.security import create_access_token;print(create_access_token(106)[0])"
 *
 * 用法：
 *   TOKEN_STUDENT=<token> TOKEN_ADMIN=<token> node scripts/shots.mjs
 * 可选：
 *   DISH_ID                指定要截的菜品（默认取高分榜第一道，数据最全）
 *   OUT                    输出目录（默认 ../docs/screenshots）
 *   CHROME_PATH            指定 Chrome 可执行文件
 */

import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawn } from 'node:child_process'

const WEB = process.env.WEB ?? 'http://127.0.0.1:5173'
const API = process.env.API ?? 'http://127.0.0.1:8000/api/v1'
const OUT = path.resolve(process.env.OUT ?? path.join(process.cwd(), '..', 'docs', 'screenshots'))
const TOKEN_STUDENT = process.env.TOKEN_STUDENT ?? ''
const TOKEN_ADMIN = process.env.TOKEN_ADMIN ?? ''

// 桌面 1440x900、移动 375x812：MacBook 主屏与 iPhone 的常见尺寸，
// 也是 README 里最省事的比例（宽度够放三列卡片，缩到 800 还认得清）
const DESKTOP = { width: 1440, height: 900 }
const MOBILE = { width: 375, height: 812 }

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function api(method, p, body, token) {
  const res = await fetch(API + p, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  return res.json()
}

async function waitServices() {
  for (const url of [API + '/dishes/tags', WEB + '/']) {
    try {
      const r = await fetch(url, { signal: AbortSignal.timeout(3000) })
      if (!r.ok) return false
    } catch {
      return false
    }
  }
  return true
}

function findChrome() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH
  const home = os.homedir()
  const candidates = [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    path.join(home, 'AppData/Local/Google/Chrome/Application/chrome.exe'),
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ]
  return candidates.find((p) => fs.existsSync(p)) ?? null
}

class Tab {
  constructor(ws) {
    this.ws = ws
    this.id = 0
    this.pending = new Map()
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      const item = this.pending.get(msg.id)
      if (!item) return
      this.pending.delete(msg.id)
      msg.error ? item.reject(new Error(JSON.stringify(msg.error))) : item.resolve(msg.result)
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

  async viewport({ width, height }, mobile = false) {
    await this.send('Emulation.setDeviceMetricsOverride', {
      width,
      height,
      deviceScaleFactor: 1,
      mobile,
    })
  }

  async goto(url, settle = 900) {
    await this.send('Page.navigate', { url })
    await sleep(settle)
  }

  async waitFor(expression, timeout = 10000) {
    const deadline = Date.now() + timeout
    while (Date.now() < deadline) {
      try {
        if (await this.eval(expression)) return true
      } catch {
        // 路由切换中途 evaluate 可能失败，重试即可
      }
      await sleep(200)
    }
    return false
  }

  /** 按可见文字点一下。比记 class 稳，样式改了也不会失效 */
  async clickText(text, scope = 'button, a, .el-button, .tag-chip, .el-tabs__item') {
    return this.eval(`(() => {
      const nodes = [...document.querySelectorAll(${JSON.stringify(scope)})];
      const hit = nodes.find((n) => n.offsetParent !== null && (n.textContent || '').trim().includes(${JSON.stringify(text)}));
      if (!hit) return false;
      hit.click();
      return true;
    })()`)
  }

  async shot(name) {
    fs.mkdirSync(OUT, { recursive: true })
    const { data } = await this.send('Page.captureScreenshot', { format: 'png' })
    fs.writeFileSync(path.join(OUT, name), Buffer.from(data, 'base64'))
    const kb = Math.round(fs.statSync(path.join(OUT, name)).size / 1024)
    console.log(`  ok   ${name.padEnd(24)} ${kb} KB`)
  }
}

/** 等页面里所有图片解码完，否则截到半个图 */
const IMAGES_SETTLED = `[...document.images].every((i) => i.complete)`

async function main() {
  // 同 e2e：全局 WebSocket 需要 Node 22+，提前说清楚
  if (typeof WebSocket === 'undefined') {
    console.error(`Node ${process.version} 没有全局 WebSocket，需要 Node 22+。`)
    process.exit(2)
  }
  if (!TOKEN_STUDENT || !TOKEN_ADMIN) {
    console.error('缺 token。先生成再跑：\n' +
      '  cd backend && .venv/Scripts/python.exe -c "from app.core.security import create_access_token;print(create_access_token(106)[0])"\n' +
      '  TOKEN_STUDENT=... TOKEN_ADMIN=... node scripts/shots.mjs')
    process.exit(2)
  }
  if (!(await waitServices())) {
    console.error('前后端没起来，先 npm run dev / 起 uvicorn')
    process.exit(2)
  }

  // 挑数据最全的一条菜品和帖子，不写死 id：换一库种子数据也能跑
  const dishId =
    process.env.DISH_ID ??
    (await api('GET', '/dishes/top?min_rating=4&min_count=1&page_size=1')).data?.[0]?.id
  const me = (await api('GET', '/users/me', null, TOKEN_STUDENT)).data

  const chromePath = findChrome()
  if (!chromePath) {
    console.error('找不到 Chrome，用 CHROME_PATH 指定')
    process.exit(2)
  }

  const port = 9500 + Math.floor(Math.random() * 90)
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'campus-shots-'))
  const chrome = spawn(chromePath, [
    '--headless=new',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    '--no-first-run',
    '--disable-gpu',
    '--hide-scrollbars',
    '--font-render-hinting=none',
    ...(process.env.CI ? ['--no-sandbox', '--disable-dev-shm-usage'] : []),
  ], { stdio: 'ignore' })

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
    if (!target) throw new Error('连不上 Chrome 调试端口')

    const ws = new WebSocket(target.webSocketDebuggerUrl)
    await new Promise((resolve, reject) => {
      ws.onopen = resolve
      ws.onerror = reject
    })
    const tab = new Tab(ws)
    await tab.send('Page.enable')
    await tab.send('Runtime.enable')
    await tab.viewport(DESKTOP)

    // token 先落到一个真实 origin 下，否则 localStorage 写到 about:blank 就丢了
    await tab.goto(WEB + '/')
    await tab.eval(`localStorage.setItem('cf_token', ${JSON.stringify(TOKEN_STUDENT)})`)

    console.log(`\n桌面 ${DESKTOP.width}×${DESKTOP.height}`)

    await tab.goto(WEB + '/')
    await tab.waitFor(`document.querySelectorAll('.postcard').length > 0`)
    await tab.waitFor(IMAGES_SETTLED)
    await tab.shot('home.png')

    await tab.goto(`${WEB}/dishes/${dishId}`)
    await tab.waitFor(`!!document.querySelector('.tag-chip')`)
    await tab.waitFor(IMAGES_SETTLED)
    await tab.shot('dish.png')

    // 标签筛选：URL 直接带 tag，等于用户点了 chip 之后的状态
    await tab.goto(`${WEB}/search?tag=${encodeURIComponent('辣')}`)
    await tab.waitFor(`!!document.querySelector('.tag-filter')`)
    await tab.waitFor(IMAGES_SETTLED)
    await tab.shot('search.png')

    await tab.goto(WEB + '/create')
    await tab.waitFor(`!!document.querySelector('.el-form, form')`)
    await tab.shot('create.png')

    // 随机一顿：首页点「帮我选」，弹窗里是后端抽出来的那道菜
    await tab.goto(WEB + '/')
    await tab.waitFor(`document.querySelectorAll('.postcard').length > 0`)
    if (await tab.clickText('帮我选')) {
      const opened = await tab.waitFor(`!!document.querySelector('.el-dialog')`, 6000)
      if (opened) {
        // 弹窗打开瞬间是「正在翻菜单…」的掷骰动画，等结果落定再截，
        // 否则截到的是三个骰子还在滚的中间态
        await tab.waitFor(
          `(() => {
            const d = document.querySelector('.el-dialog');
            return !!d && !d.textContent.includes('正在翻菜单');
          })()`,
          8000,
        )
        await tab.waitFor(IMAGES_SETTLED)
        await sleep(500)
        await tab.shot('random.png')
        await tab.eval(`document.querySelector('.el-dialog__headerbtn')?.click()`)
      }
    }

    await tab.goto(WEB + '/notifications')
    await tab.waitFor(`!!document.querySelector('.el-empty, .notify-item, .notification-item')`, 6000)
    await tab.shot('notifications.png')

    // 我赞过的：进个人中心后切页签，截的是「点过赞之后能找到回去的路」
    await tab.goto(`${WEB}/users/${me.id}`)
    await tab.waitFor(`!!document.querySelector('.el-tabs__item')`)
    await tab.clickText('我赞过的', '.el-tabs__item')
    await sleep(900)
    await tab.waitFor(IMAGES_SETTLED)
    await tab.shot('profile-liked.png')

    // 管理端：换管理员 token，同一标签页直接改 localStorage 再走一次路由
    await tab.eval(`localStorage.setItem('cf_token', ${JSON.stringify(TOKEN_ADMIN)})`)
    await tab.goto(WEB + '/admin')
    await tab.waitFor(`!!document.querySelector('.stat-card, .el-card')`, 8000)
    await sleep(600)
    await tab.shot('admin.png')

    console.log(`\n移动 ${MOBILE.width}×${MOBILE.height}`)
    await tab.eval(`localStorage.setItem('cf_token', ${JSON.stringify(TOKEN_STUDENT)})`)
    await tab.viewport(MOBILE, true)

    await tab.goto(WEB + '/')
    await tab.waitFor(`document.querySelectorAll('.postcard').length > 0`)
    await tab.waitFor(IMAGES_SETTLED)
    await tab.shot('mobile-home.png')

    await tab.goto(`${WEB}/dishes/${dishId}`)
    await tab.waitFor(`!!document.querySelector('.tag-chip')`)
    await tab.waitFor(IMAGES_SETTLED)
    await tab.shot('mobile-dish.png')

    await tab.goto(`${WEB}/notifications`)
    await sleep(900)
    await tab.shot('mobile-notifications.png')

    console.log(`\n共 ${fs.readdirSync(OUT).filter((f) => f.endsWith('.png')).length} 张 → ${OUT}`)
  } finally {
    chrome.kill()
    // 同 e2e：等进程退出再删，清理失败不顶掉真正的报错
    await new Promise((resolve) => {
      if (chrome.exitCode !== null || chrome.signalCode !== null) return resolve()
      const timer = setTimeout(resolve, 3000)
      chrome.once('exit', () => {
        clearTimeout(timer)
        resolve()
      })
    })
    try {
      fs.rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 })
    } catch (err) {
      console.warn(`临时目录没删干净（不影响结果）：${profile} ${err.code ?? ''}`)
    }
  }
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
