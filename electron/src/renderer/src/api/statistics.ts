import { requestData } from './client'
import type { StatisticsMonthlyData } from '../types/statistics'

export function getMonthlyStatistics(month: string): Promise<StatisticsMonthlyData> {
  return requestData({ method: 'GET', url: '/api/v1/statistics/monthly', params: { month } })
}
