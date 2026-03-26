/**
 * Assessment form utilities.
 * Data structures and validation logic separated from UI.
 */
import {
  AGE_MIN, AGE_MAX, GENDER_OPTIONS, FOOD_INTAKE_OPTIONS, PREVIOUS_MEDICATION_OPTIONS,
  GLUCOSE_MIN, GLUCOSE_MAX, BMI_MIN, BMI_MAX, HBA1C_MIN, HBA1C_MAX, WEIGHT_MIN, WEIGHT_MAX,
  IOB_MAX_UNITS, ANTICIPATED_CARBS_MAX_G,
  MEAL_CONTEXT_OPTIONS, ACTIVITY_CONTEXT_OPTIONS,
} from '../constants'

function defaultMeasurementTimeLocal() {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

export const NUMERIC_FIELDS = [
  { key: 'glucose_level', label: 'Glucose (mg/dL) *', required: true },
  { key: 'BMI', label: 'BMI (optional)' },
  { key: 'HbA1c', label: 'HbA1c % (optional)' },
  { key: 'weight', label: 'Weight kg (optional)' },
]
export const NUMERIC_OPTIONAL_KEYS = ['physical_activity', 'insulin_sensitivity', 'sleep_hours', 'creatinine', 'family_history']
export const DOSING_CONTEXT_KEYS = ['iob', 'anticipated_carbs', 'glucose_trend']
export const DEFAULT_AGE = '30'

export function initialForm() {
  const o = { patient_id: '', medication_name: '' }
  o.age = DEFAULT_AGE
  o.measurement_time = defaultMeasurementTimeLocal()
  o.meal_context = 'fasting'
  o.activity_context = 'resting'
  NUMERIC_FIELDS.forEach(({ key }) => { o[key] = '' })
  NUMERIC_OPTIONAL_KEYS.forEach((key) => { o[key] = '' })
  DOSING_CONTEXT_KEYS.forEach((key) => { o[key] = '' })
  o.gender = 'Male'
  o.food_intake = 'Medium'
  o.previous_medications = 'None'
  return o
}

export function validateForm(form) {
  const errors = []
  _validateMeasurementContext(form, errors)
  _validateAge(form, errors)
  _validateGender(form, errors)
  _validateFoodIntake(form, errors)
  _validatePreviousMedications(form, errors)
  _validateGlucose(form, errors)
  _validateOptionalNumeric(form, errors)
  return errors
}

function _validateMeasurementContext(form, errors) {
  const mt = String(form.measurement_time || '').trim()
  if (!mt) {
    errors.push({ field: 'measurement_time', message: 'Measurement date & time is required.' })
    return
  }
  const t = Date.parse(mt)
  if (Number.isNaN(t)) {
    errors.push({ field: 'measurement_time', message: 'Measurement time must be a valid date and time.' })
  }
  const meal = String(form.meal_context || '').trim()
  if (!meal || !MEAL_CONTEXT_OPTIONS.includes(meal)) {
    errors.push({ field: 'meal_context', message: `Meal context is required (${MEAL_CONTEXT_OPTIONS.join(', ')}).` })
  }
  const act = String(form.activity_context || '').trim()
  if (!act || !ACTIVITY_CONTEXT_OPTIONS.includes(act)) {
    errors.push({ field: 'activity_context', message: `Activity context is required (${ACTIVITY_CONTEXT_OPTIONS.join(', ')}).` })
  }
}

function _validateAge(form, errors) {
  const ageVal = form.age !== '' && form.age != null ? Number(form.age) : null
  if (ageVal === null || ageVal === '') {
    errors.push({ field: 'age', message: 'Age is required.' })
    return
  }
  if (Number.isNaN(ageVal)) {
    errors.push({ field: 'age', message: 'Age must be a number.' })
    return
  }
  if (ageVal < AGE_MIN || ageVal > AGE_MAX) {
    errors.push({ field: 'age', message: `Age must be between ${AGE_MIN} and ${AGE_MAX}.` })
    return
  }
  if (ageVal !== Math.floor(ageVal)) {
    errors.push({ field: 'age', message: 'Age must be a whole number.' })
  }
}

function _validateGender(form, errors) {
  const gender = String(form.gender || '').trim()
  if (!gender) {
    errors.push({ field: 'gender', message: 'Gender is required.' })
    return
  }
  if (!GENDER_OPTIONS.includes(gender)) {
    errors.push({ field: 'gender', message: `Gender must be one of: ${GENDER_OPTIONS.join(', ')}.` })
  }
}

function _validateFoodIntake(form, errors) {
  const food = String(form.food_intake || '').trim()
  if (!food) {
    errors.push({ field: 'food_intake', message: 'Food intake is required.' })
    return
  }
  if (!FOOD_INTAKE_OPTIONS.includes(food)) {
    errors.push({ field: 'food_intake', message: `Food intake must be one of: ${FOOD_INTAKE_OPTIONS.join(', ')}.` })
  }
}

function _validatePreviousMedications(form, errors) {
  const prevMed = String(form.previous_medications || '').trim()
  if (!prevMed) {
    errors.push({ field: 'previous_medications', message: 'Previous medication is required.' })
    return
  }
  if (!PREVIOUS_MEDICATION_OPTIONS.includes(prevMed)) {
    errors.push({ field: 'previous_medications', message: `Previous medication must be one of: ${PREVIOUS_MEDICATION_OPTIONS.join(', ')}.` })
    return
  }
  if (prevMed === 'Oral') {
    const medName = String(form.medication_name || '').trim()
    if (!medName) {
      errors.push({ field: 'medication_name', message: 'Medication name is required when Previous medication is Oral.' })
    }
  }
}

function _validateGlucose(form, errors) {
  const gl = form.glucose_level !== '' && form.glucose_level != null ? Number(form.glucose_level) : null
  if (gl === null || gl === '') {
    errors.push({ field: 'glucose_level', message: 'Glucose level is required for recommendation.' })
    return
  }
  if (Number.isNaN(gl)) {
    errors.push({ field: 'glucose_level', message: 'Glucose must be a number.' })
    return
  }
  if (gl < GLUCOSE_MIN || gl > GLUCOSE_MAX) {
    errors.push({ field: 'glucose_level', message: `Glucose must be between ${GLUCOSE_MIN} and ${GLUCOSE_MAX} mg/dL. Enter a valid reading.` })
  }
}

function _validateOptionalNumeric(form, errors) {
  const checks = [
    { key: 'BMI', val: form.BMI, min: BMI_MIN, max: BMI_MAX, label: 'BMI' },
    { key: 'HbA1c', val: form.HbA1c, min: HBA1C_MIN, max: HBA1C_MAX, label: 'HbA1c' },
    { key: 'weight', val: form.weight, min: WEIGHT_MIN, max: WEIGHT_MAX, label: 'Weight' },
  ]
  for (const { key, val, min, max, label } of checks) {
    const num = val !== '' && val != null ? Number(val) : null
    if (num == null || num === '') continue
    if (Number.isNaN(num)) {
      errors.push({ field: key, message: `${label} must be a number.` })
      continue
    }
    if (num < min || num > max) {
      errors.push({ field: key, message: `${label} must be between ${min} and ${max}. Enter a valid value.` })
    }
  }
}

export function buildBody(form) {
  const body = {}
  if (form.patient_id) body.patient_id = form.patient_id
  if (form.measurement_time) {
    const iso = new Date(form.measurement_time)
    body.measurement_time = Number.isNaN(iso.getTime()) ? String(form.measurement_time) : iso.toISOString()
  }
  if (form.meal_context) body.meal_context = String(form.meal_context).trim()
  if (form.activity_context) body.activity_context = String(form.activity_context).trim()
  if (form.age !== '' && form.age != null) body.age = Number(form.age)
  if (form.gender) body.gender = form.gender
  if (form.food_intake) body.food_intake = form.food_intake
  if (form.previous_medications) body.previous_medications = form.previous_medications
  if (form.previous_medications === 'Oral' && form.medication_name) {
    body.medication_name = String(form.medication_name).trim()
  }
  NUMERIC_FIELDS.forEach(({ key }) => {
    if (form[key] !== '' && form[key] != null) body[key] = Number(form[key])
  })
  NUMERIC_OPTIONAL_KEYS.forEach((key) => {
    if (form[key] !== '' && form[key] != null) {
      body[key] = key === 'family_history' ? String(form[key]) : Number(form[key])
    }
  })
  if (form.iob !== '' && form.iob != null && !Number.isNaN(Number(form.iob))) {
    const units = Number(form.iob)
    body.iob = Math.min(IOB_MAX_UNITS, Math.max(0, units)) / 100
  }
  if (form.anticipated_carbs !== '' && form.anticipated_carbs != null && !Number.isNaN(Number(form.anticipated_carbs))) {
    body.anticipated_carbs = Number(form.anticipated_carbs)
  }
  if (form.glucose_trend && String(form.glucose_trend).trim()) {
    body.glucose_trend = String(form.glucose_trend).trim().toLowerCase()
  }
  return body
}
