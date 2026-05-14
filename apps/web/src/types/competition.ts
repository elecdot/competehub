export interface CompetitionSummary {
  id: number
  title: string
  category?: string
  organizer?: string
  status: string
  tags: string[]
  nextNodeAt?: string
}
