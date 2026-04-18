import { describe, it, expect } from 'vitest'
import { mapServerRoleToUiRole } from './mealPlanAuth'

describe('mapServerRoleToUiRole', () => {
  it('treats clinician and admin as clinician UI role', () => {
    expect(mapServerRoleToUiRole('clinician')).toBe('clinician')
    expect(mapServerRoleToUiRole('admin')).toBe('clinician')
  })

  it('treats patient and unknown as patient', () => {
    expect(mapServerRoleToUiRole('patient')).toBe('patient')
    expect(mapServerRoleToUiRole('')).toBe('patient')
  })
})
