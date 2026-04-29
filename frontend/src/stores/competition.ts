import { defineStore } from 'pinia';
import type { Competition } from '@/api/types';

interface CompetitionState {
  filters: Record<string, unknown>;
  items: Competition[];
}

export const useCompetitionStore = defineStore('competition', {
  state: (): CompetitionState => ({
    filters: {
      keyword: '',
      category: '',
      level: '',
      sort: 'deadline',
    },
    items: [],
  }),
  actions: {
    setFilters(filters: Record<string, unknown>) {
      this.filters = { ...this.filters, ...filters };
    },
    setItems(items: Competition[]) {
      this.items = items;
    },
  },
});

