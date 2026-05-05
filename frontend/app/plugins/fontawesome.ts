import { config, library } from '@fortawesome/fontawesome-svg-core'
import {
  faBell,
  faBookOpen,
  faBriefcase,
  faBuilding,
  faChartColumn,
  faCircleCheck,
  faCloud,
  faComment,
  faEllipsis,
  faFileCircleCheck,
  faFileLines,
  faGear,
  faHouse,
  faMoneyBill,
  faUser,
} from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

// Empêche FA d'injecter automatiquement son CSS dans <head> :
// la CSP `style-src 'self' 'unsafe-inline'` l'accepte mais ce n'est
// pas nécessaire (les SVG inline reçoivent leurs dimensions via Tailwind).
config.autoAddCss = false

library.add(
  faBell,
  faBookOpen,
  faBriefcase,
  faBuilding,
  faChartColumn,
  faCircleCheck,
  faCloud,
  faComment,
  faEllipsis,
  faFileCircleCheck,
  faFileLines,
  faGear,
  faHouse,
  faMoneyBill,
  faUser,
)

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.component('FontAwesomeIcon', FontAwesomeIcon)
})
