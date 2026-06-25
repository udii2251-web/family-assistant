export interface FamilyMember {
  id: number
  name: string
  type: 'adult' | 'child' | 'dog'
  age: number | null
  weight: number | null
  breed: string | null
}

export interface ItemCategory {
  id: number
  name: string
  icon: string | null
}

export interface Item {
  id: number
  name: string
  category_id: number | null
  unit: string
  typical_size: number | null
  target_audience: string
}

export interface InventoryItem {
  item_id: number
  item_name: string
  unit: string
  remaining: number
  avg_daily_rate: number | null
  estimated_empty_date: string | null
  days_until_empty: number | null
}

export interface Alert {
  id: number
  item_id: number
  alert_date: string
  estimated_empty_date: string | null
  suggested_quantity: number | null
  status: 'pending' | 'notified' | 'done'
  message: string | null
}

export interface ChatRequest {
  message: string
}

export interface ChatResponse {
  reply: string
  actions: Array<{ tool: string; args: Record<string, unknown>; result: string }>
}
