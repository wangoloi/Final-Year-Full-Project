import { useEffect, useRef, useCallback } from 'react'
import { useClinical } from '../context/ClinicalContext'
import {
  getStableSyntheticSsoEmail,
  provisionMealPlanSession,
  postMealPlanTokenToIframeWithRetries,
  postMealPlanLogoutToIframe,
} from '../utils/mealPlanSso'
import { getMealPlanOrigin } from '../constants'

function getIframePostMessageTarget(iframeRef) {
  try {
    const src = iframeRef?.current?.src
    if (src) return new URL(src).origin
  } catch (_) {}
  return getMealPlanOrigin()
}

/**
 * After GlucoSense login, provisions a Meal Plan JWT and postMessages it into the iframe
 * so clinicians and patients are not prompted to log in again inside the meal app.
 */
export function useMealPlanSsoBridge(iframeRef) {
  const { isSignedIn, userRole, userProfile, setUserProfile } = useClinical()
  const lastSentKey = useRef('')
  const syntheticSaved = useRef(false)

  const pushToken = useCallback(async () => {
    const win = iframeRef?.current?.contentWindow
    if (!win || !isSignedIn || !userRole) return
    let email = userProfile?.email?.trim()
    if (!email) {
      email = getStableSyntheticSsoEmail(userRole, userProfile?.displayName)
      if (!syntheticSaved.current) {
        syntheticSaved.current = true
        setUserProfile({ email })
      }
    }
    const key = `${email}:${userRole}`
    try {
      const token = await provisionMealPlanSession({
        email,
        displayName: userProfile?.displayName,
        role: userRole,
      })
      const mealOrigin = getIframePostMessageTarget(iframeRef)
      postMealPlanTokenToIframeWithRetries(win, token, mealOrigin)
      lastSentKey.current = key
    } catch (e) {
      console.warn('[GlucoSense] Meal Plan SSO:', e.message || e)
    }
  }, [iframeRef, isSignedIn, userRole, userProfile?.email, userProfile?.displayName, setUserProfile])

  useEffect(() => {
    if (!isSignedIn) return undefined
    const onSignOut = () => {
      const win = iframeRef?.current?.contentWindow
      postMealPlanLogoutToIframe(win, getIframePostMessageTarget(iframeRef))
      lastSentKey.current = ''
    }
    window.addEventListener('glucosense:sign-out', onSignOut)
    return () => window.removeEventListener('glucosense:sign-out', onSignOut)
  }, [isSignedIn, iframeRef])

  useEffect(() => {
    if (!isSignedIn || !userRole) return undefined
    const email = userProfile?.email?.trim()
    const key = email ? `${email}:${userRole}` : null
    if (key && lastSentKey.current === key && iframeRef?.current?.contentWindow) {
      return undefined
    }
    const id = window.setTimeout(() => {
      pushToken()
    }, 400)
    return () => window.clearTimeout(id)
  }, [isSignedIn, userRole, userProfile?.email, userProfile?.displayName, pushToken, iframeRef])

  const onIframeLoad = useCallback(() => {
    if (!isSignedIn) return
    lastSentKey.current = ''
    window.setTimeout(() => pushToken(), 300)
  }, [isSignedIn, pushToken])

  return { onIframeLoad }
}
