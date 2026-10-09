/**
 * Resilient WebSocket Telemetry & Event Client for OutOfOffice AI
 */

import { WebSocketEvent } from '../types';

export type EventCallback = (event: WebSocketEvent) => void;

export class WebSocketClient {
  private socket: WebSocket | null = null;
  private currentJobId: string | null = null;
  private listeners: Set<EventCallback> = new Set();
  private reconnectTimeout: number | null = null;
  private pingInterval: number | null = null;
  private shouldReconnect = true;
  private isConnecting = false;

  constructor() {}

  /** Connects to telemetry stream for a specific job */
  public connectJob(jobId: string): void {
    if (this.currentJobId === jobId && this.socket && this.socket.readyState === WebSocket.OPEN) {
      return;
    }
    this.currentJobId = jobId;
    this.shouldReconnect = true;
    this.initSocket(`/ws/jobs/${jobId}`);
  }

  /** Connects to global dashboard telemetry stream */
  public connectGlobal(): void {
    if (this.currentJobId === 'global' && this.socket && this.socket.readyState === WebSocket.OPEN) {
      return;
    }
    this.currentJobId = 'global';
    this.shouldReconnect = true;
    this.initSocket('/ws/dashboard');
  }

  /** Subscribes to incoming telemetry events */
  public subscribe(callback: EventCallback): () => void {
    this.listeners.add(callback);
    return () => {
      this.listeners.delete(callback);
    };
  }

  /** Closes active connection */
  public disconnect(): void {
    this.shouldReconnect = false;
    this.clearTimers();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.currentJobId = null;
    this.isConnecting = false;
  }

  private initSocket(path: string): void {
    if (this.isConnecting) return;
    this.clearTimers();

    if (this.socket) {
      try {
        this.socket.close();
      } catch {
        // Ignore close errors on stale sockets
      }
      this.socket = null;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}${path}`;

    this.isConnecting = true;

    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        this.isConnecting = false;
        // Start ping heartbeat every 20 seconds
        this.pingInterval = window.setInterval(() => {
          if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send('ping');
          }
        }, 20000);
      };

      this.socket.onmessage = (event: MessageEvent) => {
        if (event.data === 'pong') return;
        try {
          const payload: WebSocketEvent = JSON.parse(event.data);
          this.listeners.forEach((listener) => {
            try {
              listener(payload);
            } catch (err) {
              console.error('Error in WebSocket listener:', err);
            }
          });
        } catch (parseErr) {
          console.warn('Non-JSON WebSocket message received:', event.data);
        }
      };

      this.socket.onclose = () => {
        this.isConnecting = false;
        this.clearTimers();
        if (this.shouldReconnect && this.currentJobId) {
          this.reconnectTimeout = window.setTimeout(() => {
            if (this.currentJobId) {
              const reconnectPath = this.currentJobId === 'global' ? '/ws/dashboard' : `/ws/jobs/${this.currentJobId}`;
              this.initSocket(reconnectPath);
            }
          }, 2500);
        }
      };

      this.socket.onerror = (err) => {
        this.isConnecting = false;
        console.warn('WebSocket connection error:', err);
      };
    } catch (e) {
      this.isConnecting = false;
      console.warn('Failed to establish WebSocket connection:', e);
    }
  }

  private clearTimers(): void {
    if (this.reconnectTimeout !== null) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.pingInterval !== null) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
}

// Global singleton WebSocket client
export const wsClient = new WebSocketClient();
