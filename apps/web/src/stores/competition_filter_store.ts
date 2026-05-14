import { defineStore } from 'pinia'

export const useCompetitionFilterStore = defineStore('competitionFilter', {
  state: () => ({
    keyword: '',
    category: '',
    grade: '',
    major: '',
    sort: 'deadline',
    page: 1,
    pageSize: 20,
  }),
})
