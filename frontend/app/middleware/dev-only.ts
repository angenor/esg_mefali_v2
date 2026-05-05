import { defineNuxtRouteMiddleware, abortNavigation } from '#imports'

// Bloque l'accès aux pages /dev/* en production (R-014).
export default defineNuxtRouteMiddleware(() => {
  if (process.env.NODE_ENV === 'production') {
    return abortNavigation({ statusCode: 404, statusMessage: 'Not Found' })
  }
})
