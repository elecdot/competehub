import { defineStore } from 'pinia'
import type { LocationQuery, LocationQueryRaw } from 'vue-router'

import type { CompetitionListParams } from '@/api/client'
import type { ParticipantForm } from '@/types/competition'

type ParticipantFormFilter = ParticipantForm | ''

function queryValue(query: LocationQuery, key: string): string {
  const value = query[key]
  return (Array.isArray(value) ? value[0] : value) ?? ''
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

function initialState() {
  return {
    keyword: '',
    category: '',
    grade: '',
    major: '',
    tag: '',
    participantForm: '' as ParticipantFormFilter,
    deadlineFrom: '',
    deadlineTo: '',
    page: 1,
    pageSize: 20,
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
        keyword: queryValue(query, 'keyword'),
        category: queryValue(query, 'category'),
        major: queryValue(query, 'major'),
        grade: queryValue(query, 'grade'),
        tag: queryValue(query, 'tag'),
        participantForm: participantForm(queryValue(query, 'participant_form')),
        deadlineFrom: isoDate(queryValue(query, 'deadline_from')),
        deadlineTo: isoDate(queryValue(query, 'deadline_to')),
        page: positiveInteger(queryValue(query, 'page'), 1),
        pageSize: positiveInteger(queryValue(query, 'page_size'), 20, 100),
      })
    },
    toRouteQuery(): LocationQueryRaw {
      const query: LocationQueryRaw = {}
      if (this.keyword) query.keyword = this.keyword
      if (this.category) query.category = this.category
      if (this.major) query.major = this.major
      if (this.grade) query.grade = this.grade
      if (this.tag) query.tag = this.tag
      if (this.participantForm) query.participant_form = this.participantForm
      if (this.deadlineFrom) query.deadline_from = this.deadlineFrom
      if (this.deadlineTo) query.deadline_to = this.deadlineTo
      if (this.page > 1) query.page = String(this.page)
      if (this.pageSize !== 20) query.page_size = String(this.pageSize)
      return query
    },
    toQueryParams(): CompetitionListParams {
      return {
        keyword: this.keyword || undefined,
        category: this.category || undefined,
        major: this.major || undefined,
        grade: this.grade || undefined,
        tag: this.tag || undefined,
        participant_form: this.participantForm || undefined,
        deadline_from: this.deadlineFrom || undefined,
        deadline_to: this.deadlineTo || undefined,
        page: this.page,
        page_size: this.pageSize,
      }
    },
  },
})
