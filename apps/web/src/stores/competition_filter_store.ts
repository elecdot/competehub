import { defineStore } from 'pinia'

import type { CompetitionListParams } from '@/api/client'
import type { ParticipantForm } from '@/types/competition'

type ParticipantFormFilter = ParticipantForm | ''

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
