import { post } from './request'
import type { LoginResult } from '@/types'

export function apiLogin(username: string, password: string) {
  return post<LoginResult>('/auth/login', { username, password })
}

export function apiRegister(username: string, nickname: string, password: string) {
  return post<LoginResult>('/auth/register', { username, nickname, password })
}
