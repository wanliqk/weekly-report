import { defineStore } from 'pinia'

import * as authApi from '@renderer/api/auth'
import { ApiError } from '@renderer/api/client'
import type { MeData } from '@renderer/types/user'

let initializationPromise: Promise<void> | null = null

export class SecureStorageUnavailableError extends Error {
  constructor() {
    super('系统安全存储当前不可用，无法安全保存登录状态')
    this.name = 'SecureStorageUnavailableError'
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: null as string | null,
    currentUser: null as MeData | null,
    initialized: false,
    systemInitialized: null as boolean | null,
    secureStorageAvailable: true,
    initializationError: null as string | null
  }),
  getters: {
    isAuthenticated: (state): boolean => state.currentUser !== null,
    isAdmin: (state): boolean => state.currentUser?.role === 'admin',
    mustChangePassword: (state): boolean => state.currentUser?.must_change_password === true
  },
  actions: {
    async initialize(): Promise<void> {
      if (this.initialized) {
        return
      }
      initializationPromise ??= this.restoreSession()
      try {
        await initializationPromise
      } finally {
        initializationPromise = null
      }
    },

    async restoreSession(): Promise<void> {
      this.initializationError = null
      try {
        const status = await authApi.getBootstrapStatus()
        this.systemInitialized = status.initialized
        const stored = await window.runtimeBridge.token.get()
        this.secureStorageAvailable = stored.available
        this.accessToken = status.initialized ? stored.token : null
        if (!status.initialized && stored.token) {
          await window.runtimeBridge.token.clear()
        }
        if (stored.token && status.initialized) {
          try {
            this.currentUser = await authApi.getMe()
          } catch (error) {
            if (error instanceof ApiError && error.code === 40102) {
              await this.clearSession()
            } else {
              this.initializationError = '恢复登录状态失败，请重新登录'
              this.currentUser = null
            }
          }
        }
      } catch {
        this.initializationError = '无法读取初始化或安全登录状态'
        this.currentUser = null
      } finally {
        this.initialized = true
      }
    },

    async bootstrap(payload: {
      username: string
      password: string
      display_name: string
    }): Promise<void> {
      await authApi.bootstrap(payload)
      this.systemInitialized = true
    },

    async login(username: string, password: string): Promise<void> {
      if (!this.secureStorageAvailable) {
        throw new SecureStorageUnavailableError()
      }
      const result = await authApi.login({ username, password })
      const stored = await window.runtimeBridge.token.set(result.access_token)
      if (!stored.available) {
        this.secureStorageAvailable = false
        throw new SecureStorageUnavailableError()
      }
      this.accessToken = result.access_token
      try {
        this.currentUser = await authApi.getMe()
      } catch (error) {
        await this.clearSession()
        throw error
      }
    },

    async changePassword(currentPassword: string, newPassword: string): Promise<void> {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword
      })
      await this.clearSession()
    },

    async logout(): Promise<void> {
      if (this.accessToken) {
        try {
          await authApi.logout()
        } catch {
          // Logout is client-side in V1; local token removal remains authoritative.
        }
      }
      await this.clearSession()
    },

    async handleTokenInvalid(): Promise<void> {
      if (this.accessToken || this.currentUser) {
        await this.clearSession()
      }
    },

    async clearSession(): Promise<void> {
      this.accessToken = null
      this.currentUser = null
      try {
        const result = await window.runtimeBridge.token.clear()
        this.secureStorageAvailable = result.available
      } catch {
        this.initializationError = '无法清除本机安全登录状态'
      }
    }
  }
})
