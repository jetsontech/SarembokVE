/**
 * Antigravity Gemini Fabric - Asynchronous Protocol Message Bus
 * Sovereign Protocol [DIRECTIVE-01]
 * 
 * Manages inter-agent message routing, dispatching, and streaming.
 */

import { randomUUID } from 'node:crypto';
import { validateProtocolMessage } from './types.js';

export class MessageBus {
  /**
   * @param {import('../memory/wal_store.js').WalStore} walStore
   */
  constructor(walStore) {
    this.walStore = walStore;
    this.handlers = new Map(); // targetAgentId -> handlerFn
    this.globalListeners = new Set();
  }

  /**
   * Register handler for a specific agent
   * @param {string} agentId
   * @param {(message: Object) => Promise<any>} handler
   */
  registerHandler(agentId, handler) {
    this.handlers.set(agentId, handler);
    return () => this.handlers.delete(agentId);
  }

  /**
   * Subscribe to all bus traffic (e.g. for monitoring / replay)
   * @param {Function} listener
   */
  subscribeAll(listener) {
    this.globalListeners.add(listener);
    return () => this.globalListeners.delete(listener);
  }

  /**
   * Send a protocol message to target agent
   * @param {Object} params
   * @param {string} params.sessionId
   * @param {string} params.from
   * @param {string} params.to
   * @param {string} params.type
   * @param {any} params.payload
   * @param {string} [params.correlationId]
   * @param {number} [params.tokenCost=0]
   */
  async send({ sessionId, from, to, type, payload, correlationId = null, tokenCost = 0 }) {
    const msg = {
      id: randomUUID(),
      sessionId,
      from,
      to,
      type,
      payload,
      correlationId: correlationId || randomUUID(),
      timestamp: Date.now(),
      tokenCost
    };

    validateProtocolMessage(msg);

    // Notify global subscribers
    for (const listener of this.globalListeners) {
      try {
        listener(msg);
      } catch (err) {
        console.error('[MessageBus] Global listener error:', err);
      }
    }

    const handler = this.handlers.get(to);
    if (!handler) {
      throw new Error(`[MessageBus] No registered handler for recipient agent '${to}'`);
    }

    return await handler(msg);
  }
}
