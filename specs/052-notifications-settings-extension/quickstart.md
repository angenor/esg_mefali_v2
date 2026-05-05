# Quickstart — F52

**Feature** : Notifications, Paramètres, Exports & Panneau d'extension
**Branche** : `052-notifications-settings-extension`
**Date** : 2026-05-05

Marche à suivre pour démarrer la feature en local et exécuter les tests d'acceptation principaux.

---

## 1. Pré-requis

- Branche `052-notifications-settings-extension` checkée.
- `make setup && make db-up && make migrate` exécutés au moins une fois.
- Variables d'env : `JWT_SECRET`, `DB_PASSWORD`, `LLM_*`, `VOYAGE_API_KEY` (déjà configurés pour les features amont).
- Navigateur Chrome ≥ 114, Edge ≥ 114 ou Brave ≥ 1.55 pour tester l'extension.

---

## 2. Migration

```bash
cd backend && source .venv/bin/activate
alembic upgrade head
```

Vérifier que les enums `notification_channel`, `deletion_status`, `export_type`, `export_status` et les tables `notification_preference`, `account_deletion_request`, `extension_ping`, `export_artifact` existent :

```bash
psql -h localhost -U postgres -d esg_mefali -c "\dt notification_preference account_deletion_request extension_ping export_artifact"
```

---

## 3. Lancer les serveurs

```bash
# Terminal 1 — Postgres
make db-up

# Terminal 2 — Backend
make backend          # http://localhost:8010

# Terminal 3 — Frontend
make frontend         # http://localhost:3001
```

---

## 4. Tester `/notifications`

1. Se connecter sur `http://localhost:3001`.
2. Côté backend, créer 12 notifications de seed :

   ```bash
   pytest tests/seed/test_seed_notifications.py -v   # ou seed manuel via fixture
   ```

3. Ouvrir `/notifications` → vérifier la liste paginée + badge "5 non-lues".
4. Cliquer "Tout marquer comme lu" → la cloche du shell repasse à 0 ; SC-002 ✅.
5. Couper la connexion réseau, recliquer "Tout marquer comme lu" → toast d'erreur + rollback visible.

---

## 5. Tester `/parametres`

### Profil + e-mail

1. Modifier nom + langue → reflété en en-tête.
2. Saisir un nouvel e-mail valide → toast "Vérifiez votre boîte mail" ; vérifier que `account_user.email_pending` est posé.
3. Cliquer le lien dans l'e-mail (cf. mailcatcher local) → e-mail principal mis à jour.

### Préférences notifications

1. Décocher `email × deadline_j_minus_30` → `PATCH /me/notification-preferences` envoie un seul update.
2. Recharger la page → l'état persiste.

### Consentements

1. Cliquer "Retirer" sur un consent actif → bottom sheet de confirmation.
2. Confirmer → audit log écrit, e-mail de confirmation envoyé, ligne refletée.

### Sessions

1. Se connecter sur un second navigateur.
2. Dans le premier, dans `Sécurité`, voir 2 sessions ; révoquer la 2ᵉ.
3. Dans le 2ᵉ navigateur, recharger → redirection vers `/login`.

### Export RGPD

1. Cliquer "Télécharger toutes mes données" → si < 100 Mo, lien direct ; sinon e-mail différé.

### Suppression compte

1. Zone dangereuse → bottom sheet → saisir la raison sociale exacte.
2. Confirmer → message indiquant la date de purge dans 30 jours, e-mail de confirmation envoyé.
3. Recliquer "Annuler la suppression" → la demande passe `cancelled`.

---

## 6. Tester `/dashboard/exports`

1. Ouvrir → tableau des exports passés.
2. Cliquer "Nouvel export" → choisir `rgpd_full / json` → bottom sheet → confirmer.
3. Attendre quelques secondes → notification SSE `system` reçue → ligne passe à `ready` avec lien actif.

---

## 7. Tester l'extension (sidepanel)

```bash
cd extension && pnpm install && pnpm build:sidepanel
```

Le build produit `extension/dist/sidepanel/`. Vérifier la taille gzip :

```bash
gzip-size extension/dist/sidepanel/assets/*.js
# total attendu < 200 kB
```

Charger l'extension :

1. Chrome → `chrome://extensions` → "Mode développeur" → "Charger l'extension non empaquetée" → sélectionner `extension/`.
2. Ouvrir une URL listée au catalogue (ex. `https://www.boad.org/...` en seed F33) → le sidepanel droit s'ouvre.
3. Vérifier que 2 candidatures actives s'affichent + 3 cartes d'offres recommandées (P2).
4. Cliquer "Reprendre" → un nouvel onglet ouvre la candidature.
5. Ouvrir `/parametres` → la section "Connecté" affiche "Extension détectée — dernier ping il y a < 1 min".

---

## 8. Tests automatisés

```bash
# Backend
cd backend && source .venv/bin/activate
pytest tests/unit/notifications -v
pytest tests/integration/users/test_account_deletion.py -v
pytest tests/integration/extension/test_sidepanel_context.py -v
pytest --cov=app --cov-report=term-missing       # gate ≥ 80 %

# Frontend
cd ../frontend
pnpm vitest run app/stores/__tests__/notificationPreferences.test.ts
pnpm vitest run app/components/parametres/__tests__/AccountDeletionBottomSheet.test.ts

# E2E
pnpm playwright test e2e/052-notifications-mark-all-read.spec.ts
pnpm playwright test e2e/052-account-deletion-30d.spec.ts
pnpm playwright test e2e/052-extension-sidepanel.spec.ts
```

---

## 9. Vérifications constitution avant PR

- [ ] P2 : tous les nouveaux endpoints sont 404 sur cross-tenant.
- [ ] P3 : audit log présent pour mutation profil, consent, deletion, session.
- [ ] P10 : aucune saisie interactive en bulle LLM ; toutes en bottom sheet.
- [ ] Sidepanel : bundle gzip < 200 kB, pas de payload tenant via `chrome.runtime` content → background.
- [ ] Coverage backend ≥ 80 %.
