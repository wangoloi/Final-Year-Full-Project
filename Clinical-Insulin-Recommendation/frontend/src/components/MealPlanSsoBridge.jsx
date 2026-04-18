import { useEffect, useRef, useCallback, useState } from 'react'
import { useClinical } from '../context/ClinicalContext'
import { getStoredMealToken } from '../auth/mealPlanAuth'
import {
  getStableSyntheticSsoEmail,
  provisionMealPlanSession,
  postMealPlanTokenToIframeWithRetries,
  postMealPlanLogoutToIframe,
} from '../utils/mealPlanSso'
import { getMealPlanOrigin } from '../constants'

const PUSH_DEBOUNCE_MS = 220

function getIframePostMessageTarget(iframeRef) {
  try {
    const src = iframeRef?.current?.src
    if (src) return new URL(src).origin
  } catch (_) {}
  return getMealPlanOrigin()
}

/**
 * When a Meal Plan JWT exists or embed provisions a session, postMessage it into the iframe.
 * GlucoSense clinical access does not require Meal Plan login; SSO is optional after linking.
 *
 * Debounces token push so iframe `onLoad` and auth effect do not double-fire (avoids visible blink).
 * Synthetic SSO email is read from localStorage only — no profile update (extra re-renders).
 */
export function useMealPlanSsoBridge(iframeRef) {
  const { isSignedIn, userRole, userProfile } = useClinical()
  const lastSentKey = useRef('')
  const pushTimerRef = useRef(null)
  const [ssoError, setSsoError] = useState(null)

  const pushToken = useCallback(async () => {
    const win = iframeRef?.current?.contentWindow
    if (!win || !isSignedIn || !userRole) return
    const ssoRole = userProfile?.mealPlanRole || userRole
    const email =
      userProfile?.email?.trim() || getStableSyntheticSsoEmail(ssoRole, userProfile?.displayName)
    const key = `${email}:${ssoRole}`
    try {
      setSsoError(null)
      const existing = getStoredMealToken()
      if (existing) {
        postMealPlanTokenToIframeWithRetries(win, existing)
        lastSentKey.current = key
        return
      }
      const token = await provisionMealPlanSession({
        email,
        displayName: userProfile?.displayName,
        role: ssoRole,
      })
      postMealPlanTokenToIframeWithRetries(win, token)
      lastSentKey.current = key
    } catch (e) {
      const msg = e?.message || String(e)
      console.warn('[GlucoSense] Meal Plan SSO:', msg)
      setSsoError(msg)
    }
  }, [iframeRef, isSignedIn, userRole, userProfile?.email, userProfile?.displayName, userProfile?.mealPlanRole])

  const schedulePush = useCallback(() => {
    if (pushTimerRef.current) window.clearTimeout(pushTimerRef.current)
    pushTimerRef.current = window.setTimeout(() => {
      pushTimerRef.current = null
      pushToken()
    }, PUSH_DEBOUNCE_MS)
  }, [pushToken])

  useEffect(() => {
    if (!isSignedIn) {
      setSsoError(null)
      return undefined
    }
    const onSignOut = () => {
      const win = iframeRef?.current?.contentWindow
      postMealPlanLogoutToIframe(win, getIframePostMessageTarget(iframeRef))
      lastSentKey.current = ''
      setSsoError(null)
    }
    window.addEventListener('glucosense:sign-out', onSignOut)
    return () => window.removeEventListener('glucosense:sign-out', onSignOut)
  }, [isSignedIn, iframeRef])

  useEffect(() => {
    if (!isSignedIn || !userRole) return undefined
    schedulePush()
    return () => {
      if (pushTimerRef.current) window.clearTimeout(pushTimerRef.current)
    }
  }, [isSignedIn, userRole, userProfile?.email, userProfile?.displayName, userProfile?.mealPlanRole, schedulePush])

  const onIframeLoad = useCallback(() => {
    if (!isSignedIn) return
    schedulePush()
  }, [isSignedIn, schedulePush])

  const dismissSsoError = useCallback(() => setSsoError(null), [])

  return { onIframeLoad, ssoError, dismissSsoError }
}
