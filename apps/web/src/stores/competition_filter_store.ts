import { defineStore } from 'pinia'
import type { LocationQuery, LocationQueryRaw } from 'vue-router'

import type { CompetitionListParams } from '@/api/client'
import type { DiscoverySort, ParticipantForm, RegistrationStatus } from '@/types/competition'

type ParticipantFormFilter = ParticipantForm | ''
type RegistrationStatusFilter = RegistrationStatus | ''

export const COMPETITION_FILTER_MAX_LENGTHS = {
  keyword: 255,
  category: 120,
  major: 120,
  grade: 40,
  tag: 120,
} as const

function queryValue(query: LocationQuery, key: string): string {
  const value = query[key]
  return (Array.isArray(value) ? value[0] : value) ?? ''
}

function normalizedText(value: string | null | undefined, maximum: number): string {
  const normalized = value?.trim() ?? ''
  return Array.from(normalized).length <= maximum ? normalized : ''
}

function queryText(query: LocationQuery, key: string, maximum: number): string {
  return normalizedText(queryValue(query, key), maximum)
}

function positiveInteger(value: string, fallback: number, maximum?: number): number {
  if (!/^\d+$/.test(value)) {
    return fallback
  }

  const parsed = Number(value)
  if (parsed < 1 || (maximum !== undefined && parsed > maximum)) {
    return fallback
  }
  return parsed
}

function isoDate(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return ''
  }

  const parsed = new Date(`${value}T00:00:00Z`)
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value
    ? value
    : ''
}

function participantForm(value: string): ParticipantFormFilter {
  return value === 'individual' || value === 'team' ? value : ''
}

function registrationStatus(value: string): RegistrationStatusFilter {
  return ['open', 'upcoming', 'closed', 'unknown', 'not_applicable'].includes(value)
    ? (value as RegistrationStatus)
    : ''
}

function discoverySort(value: string): DiscoverySort {
  return ['actionable', 'registration_deadline', 'published_at'].includes(value)
    ? (value as DiscoverySort)
    : 'actionable'
}

function initialState() {
  return {
    keyword: '',
    category: '',
    grade: '',
    major: '',
    tag: '',
    registrationStatus: '' as RegistrationStatusFilter,
    participantForm: '' as ParticipantFormFilter,
    deadlineFrom: '',
    deadlineTo: '',
    page: 1,
    pageSize: 20,
    sort: 'actionable' as DiscoverySort,
  }
}

export const useCompetitionFilterStore = defineStore('competitionFilter', {
  state: initialState,
  actions: {
    reset() {
      this.$patch(initialState())
    },
    replaceFromRouteQuery(query: LocationQuery) {
      this.$patch({
        keyword: queryText(query, 'keyword', COMPETITION_FILTER_MAX_LENGTHS.keyword),
        category: queryText(query, 'category', COMPETITION_FILTER_MAX_LENGTHS.category),
        major: queryText(query, 'major', COMPETITION_FILTER_MAX_LENGTHS.major),
        grade: queryText(query, 'grade', COMPETITION_FILTER_MAX_LENGTHS.grade),
        tag: queryText(query, 'tag', COMPETITION_FILTER_MAX_LENGTHS.tag),
        registrationStatus: registrationStatus(queryValue(query, 'registration_status')),
        participantForm: participantForm(queryValue(query, 'participant_form')),
        deadlineFrom: isoDate(queryValue(query, 'deadline_from')),
        deadlineTo: isoDate(queryValue(query, 'deadline_to')),
        page: positiveInteger(queryValue(query, 'page'), 1),
        pageSize: positiveInteger(queryValue(query, 'page_size'), 20, 100),
        sort: discoverySort(queryValue(query, 'sort')),
      })
    },
    toRouteQuery(): LocationQueryRaw {
      const query: LocationQueryRaw = {}
      const keyword = normalizedText(this.keyword, COMPETITION_FILTER_MAX_LENGTHS.keyword)
      const category = normalizedText(this.category, COMPETITION_FILTER_MAX_LENGTHS.category)
      const major = normalizedText(this.major, COMPETITION_FILTER_MAX_LENGTHS.major)
      const grade = normalizedText(this.grade, COMPETITION_FILTER_MAX_LENGTHS.grade)
      const tag = normalizedText(this.tag, COMPETITION_FILTER_MAX_LENGTHS.tag)
      if (keyword) query.keyword = keyword
      if (category) query.category = category
      if (major) query.major = major
      if (grade) query.grade = grade
      if (tag) query.tag = tag
      if (this.registrationStatus) query.registration_status = this.registrationStatus
      if (this.participantForm) query.participant_form = this.participantForm
      if (this.deadlineFrom) query.deadline_from = this.deadlineFrom
      if (this.deadlineTo) query.deadline_to = this.deadlineTo
      if (this.page > 1) query.page = String(this.page)
      if (this.pageSize !== 20) query.page_size = String(this.pageSize)
      if (this.sort !== 'actionable') query.sort = this.sort
      return query
    },
    toQueryParams(): CompetitionListParams {
      return {
        keyword:
          normalizedText(this.keyword, COMPETITION_FILTER_MAX_LENGTHS.keyword) || undefined,
        category:
          normalizedText(this.category, COMPETITION_FILTER_MAX_LENGTHS.category) || undefined,
        major: normalizedText(this.major, COMPETITION_FILTER_MAX_LENGTHS.major) || undefined,
        grade: normalizedText(this.grade, COMPETITION_FILTER_MAX_LENGTHS.grade) || undefined,
        tag: normalizedText(this.tag, COMPETITION_FILTER_MAX_LENGTHS.tag) || undefined,
        registration_status: this.registrationStatus || undefined,
        participant_form: this.participantForm || undefined,
        deadline_from: this.deadlineFrom || undefined,
        deadline_to: this.deadlineTo || undefined,
        page: this.page,
        page_size: this.pageSize,
        sort: this.sort,
      }
    },
  },
})
