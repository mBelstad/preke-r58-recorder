/**
 * Vitest Test Setup
 * Global test configuration and mocks
 */
import { vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// ============================================
// WebSocket Mock
// ============================================
export class MockWebSocket {
  static instances: MockWebSocket[] = []
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  url: string
  readyState: number = MockWebSocket.CONNECTING
  
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null

  private sentMessages: string[] = []

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
    
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen?.(new Event('open'))
    }, 0)
  }

  send(data: string): void {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open')
    }
    this.sentMessages.push(data)
  }

  close(code?: number, reason?: string): void {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close', { code, reason }))
  }

  // Test helpers
  simulateMessage(data: object): void {
    this.onmessage?.(new MessageEvent('message', { 
      data: JSON.stringify(data) 
    }))
  }

  simulateError(error: Error): void {
    this.onerror?.(new ErrorEvent('error', { error }))
  }

  simulateClose(code = 1000, reason = ''): void {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close', { code, reason }))
  }

  getSentMessages(): string[] {
    return [...this.sentMessages]
  }

  getLastSentMessage(): object | null {
    const last = this.sentMessages[this.sentMessages.length - 1]
    return last ? JSON.parse(last) : null
  }

  static reset(): void {
    MockWebSocket.instances = []
  }

  static getLastInstance(): MockWebSocket | null {
    return MockWebSocket.instances[MockWebSocket.instances.length - 1] || null
  }
}

// Stub WebSocket globally
vi.stubGlobal('WebSocket', MockWebSocket)

// ============================================
// Fetch Mock
// ============================================
export const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

export function mockFetchResponse(data: unknown, status = 200): void {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  })
}

export function mockFetchError(message: string): void {
  mockFetch.mockRejectedValueOnce(new Error(message))
}

// ============================================
// PostMessage Mock (for VDO.ninja iframe)
// ============================================
export const mockPostMessage = vi.fn()

export function createMockIframe(): HTMLIFrameElement {
  const iframe = document.createElement('iframe')
  Object.defineProperty(iframe, 'contentWindow', {
    value: {
      postMessage: mockPostMessage,
    },
    writable: true,
  })
  return iframe
}

// ============================================
// Timer Mocks
// ============================================
export function useFakeTimers(): void {
  vi.useFakeTimers()
}

export function useRealTimers(): void {
  vi.useRealTimers()
}

// ============================================
// LocalStorage Mock
// ============================================
const localStorageData: Record<string, string> = {}

const mockLocalStorage = {
  getItem: vi.fn((key: string) => localStorageData[key] || null),
  setItem: vi.fn((key: string, value: string) => {
    localStorageData[key] = value
  }),
  removeItem: vi.fn((key: string) => {
    delete localStorageData[key]
  }),
  clear: vi.fn(() => {
    Object.keys(localStorageData).forEach(key => delete localStorageData[key])
  }),
  get length() {
    return Object.keys(localStorageData).length
  },
  key: vi.fn((index: number) => Object.keys(localStorageData)[index] || null),
}

vi.stubGlobal('localStorage', mockLocalStorage)

// ============================================
// Global Setup/Teardown
// ============================================
beforeEach(() => {
  // Fresh Pinia store for each test
  setActivePinia(createPinia())
  
  // Reset mocks
  MockWebSocket.reset()
  mockFetch.mockReset()
  mockPostMessage.mockReset()
  mockLocalStorage.clear()
  
  // Reset timers if using fake timers
  vi.clearAllTimers()
})

afterEach(() => {
  vi.clearAllMocks()
})

// ============================================
// Test Utilities
// ============================================
export async function flushPromises(): Promise<void> {
  await new Promise(resolve => setTimeout(resolve, 0))
}

export function createMockEvent<T extends object>(
  type: string,
  payload: T
): { v: number; type: string; ts: string; seq: number; device_id: string; payload: T } {
  return {
    v: 1,
    type,
    ts: new Date().toISOString(),
    seq: 1,
    device_id: 'test-device-001',
    payload,
  }
}

