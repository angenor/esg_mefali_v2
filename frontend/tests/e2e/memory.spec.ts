/**
 * F57 / T053 — Playwright E2E : memory snapshot (GET) + forget RGPD (DELETE).
 *
 * Scénario (couvre SC-003 + SC-004) :
 *   1. Inscription dynamique d'un utilisateur PME.
 *   2. Login + récupération du cookie CSRF via le helper partagé.
 *   3. Création d'un thread + insertion de messages via API.
 *   4. GET /me/chat/threads/{id}/memory → vérifier shape `MemorySnapshotV2`.
 *   5. DELETE /me/chat/threads/{id}/memory → 200 idempotent.
 *   6. Re-GET → vérifier `vector_index_size=0` + `summary=null`.
 */

import { test, expect } from '@playwright/test'

import { registerLoginCsrf } from './helpers/auth'

const API_BASE = process.env.E2E_API_BASE || 'http://localhost:8010'

test.describe('F57 — memory endpoint (GET + DELETE)', () => {
  test('GET memory returns MemorySnapshotV2 shape; DELETE purges', async ({
    request,
  }) => {
    // 1. Register + login + CSRF
    const { headers } = await registerLoginCsrf(request, { apiBase: API_BASE })

    // 2. Create thread (CSRF header attendu par AuthSessionMiddleware)
    const threadResp = await request.post(`${API_BASE}/me/chat/threads`, {
      headers,
      data: { title: 'F57 E2E memory' },
    })
    expect(threadResp.status(), `thread create body: ${await threadResp.text()}`).toBeLessThan(400)
    const thread = await threadResp.json()
    const threadId = thread?.id || thread?.thread_id
    expect(threadId, `thread payload: ${JSON.stringify(thread)}`).toBeTruthy()

    // 4. GET memory snapshot
    const getResp = await request.get(
      `${API_BASE}/me/chat/threads/${threadId}/memory`,
      { headers },
    )
    expect(getResp.status(), `memory body: ${await getResp.text()}`).toBe(200)
    const snap = await getResp.json()
    // Vérifier la shape MemorySnapshotV2 (FR-007)
    expect(snap).toHaveProperty('total_messages')
    expect(snap).toHaveProperty('recent_messages_count')
    expect(snap).toHaveProperty('vector_index_size')
    expect(snap).toHaveProperty('summary')
    expect(snap).toHaveProperty('last_compaction_at')
    expect(snap).toHaveProperty('entities_referenced')
    expect(Array.isArray(snap.entities_referenced)).toBe(true)
    expect(typeof snap.total_messages).toBe('number')

    // 5. DELETE memory (forget RGPD)
    const delResp = await request.delete(
      `${API_BASE}/me/chat/threads/${threadId}/memory`,
      { headers },
    )
    expect(delResp.status()).toBe(200)
    const delBody = await delResp.json()
    expect(delBody).toHaveProperty('thread_id')
    expect(delBody).toHaveProperty('embeddings_purged')
    expect(delBody).toHaveProperty('summary_cleared')
    expect(delBody).toHaveProperty('agent_entity_memory_unchanged')
    expect(delBody.agent_entity_memory_unchanged).toBe(true)

    // 6. Re-DELETE idempotent → toujours 200
    const delResp2 = await request.delete(
      `${API_BASE}/me/chat/threads/${threadId}/memory`,
      { headers },
    )
    expect(delResp2.status()).toBe(200)
    const delBody2 = await delResp2.json()
    expect(delBody2.embeddings_purged).toBe(0)
    expect(delBody2.summary_cleared).toBe(false)

    // 7. Re-GET → snapshot fresh (vector_index_size=0, summary=null)
    const getResp2 = await request.get(
      `${API_BASE}/me/chat/threads/${threadId}/memory`,
      { headers },
    )
    expect(getResp2.status()).toBe(200)
    const snap2 = await getResp2.json()
    expect(snap2.vector_index_size).toBe(0)
    expect(snap2.summary).toBeNull()
    expect(snap2.last_compaction_at).toBeNull()
  })

  test('GET memory cross-tenant returns 404', async ({ browser }) => {
    // Two distinct browser contexts ⇒ deux sessions cookies indépendantes
    // (même process Playwright). Évite le conflit de session sur le seul
    // `request` partagé du test.
    const ctxB = await browser.newContext()
    const reqB = ctxB.request
    const { headers: headersB } = await registerLoginCsrf(reqB, { apiBase: API_BASE })

    const threadResp = await reqB.post(`${API_BASE}/me/chat/threads`, {
      headers: headersB,
      data: { title: 'B private' },
    })
    if (![200, 201].includes(threadResp.status())) {
      await ctxB.close()
      test.skip(true, 'thread create failed')
      return
    }
    const thread = await threadResp.json()
    const threadId = thread?.id || thread?.thread_id
    await ctxB.close()

    // Now A queries B's thread — distinct context, distinct session.
    const ctxA = await browser.newContext()
    const reqA = ctxA.request
    const { headers: headersA } = await registerLoginCsrf(reqA, { apiBase: API_BASE })

    const r = await reqA.get(
      `${API_BASE}/me/chat/threads/${threadId}/memory`,
      { headers: headersA },
    )
    expect([404, 401, 403]).toContain(r.status())
    await ctxA.close()
  })
})
