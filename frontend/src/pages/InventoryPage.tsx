import { useState, useEffect } from 'react'
import { AlertTriangle, Package } from 'lucide-react'
import { getInventory } from '../api'
import type { InventoryItem } from '../types'

export default function InventoryPage() {
  const [inventory, setInventory] = useState<InventoryItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getInventory().then(setInventory).finally(() => setLoading(false))
  }, [])

  const getUrgencyColor = (days: number | null) => {
    if (days === null || days === undefined) return 'bg-gray-100 text-gray-600'
    if (days <= 3) return 'bg-red-100 text-red-700'
    if (days <= 7) return 'bg-yellow-100 text-yellow-700'
    return 'bg-green-100 text-green-700'
  }

  if (loading) return <div className="p-8 text-center text-gray-400">加载中...</div>

  return (
    <div className="p-4 md:p-8">
      <h2 className="text-xl font-bold mb-1">库存总览</h2>
      <p className="text-sm text-gray-500 mb-6">查看所有物品的剩余量和预计耗尽日期</p>

      {/* Alert items */}
      {inventory.filter(i => i.days_until_empty !== null && i.days_until_empty <= 3).length > 0 && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="text-red-500" size={20} />
            <span className="font-semibold text-red-700">需要补货</span>
          </div>
          {inventory
            .filter(i => i.days_until_empty !== null && i.days_until_empty <= 3)
            .map(item => (
              <div key={item.item_id} className="flex items-center justify-between py-1 text-sm">
                <span className="font-medium">{item.item_name}</span>
                <span className="text-red-600">
                  还剩 {item.remaining} {item.unit}，约 {item.days_until_empty} 天后用完
                </span>
              </div>
            ))}
        </div>
      )}

      {/* All items grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {inventory.map(item => (
          <div key={item.item_id} className="bg-white rounded-xl p-4 border shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Package size={18} className="text-gray-400" />
                <span className="font-semibold">{item.item_name}</span>
              </div>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${getUrgencyColor(item.days_until_empty)}`}>
                {item.days_until_empty === null
                  ? '无数据'
                  : `${item.days_until_empty}天`}
              </span>
            </div>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">剩余</span>
                <span className="font-medium">{item.remaining} {item.unit}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">日均消耗</span>
                <span>{item.avg_daily_rate?.toFixed(2) ?? '暂无'} {item.unit}/天</span>
              </div>
              {item.estimated_empty_date && (
                <div className="flex justify-between">
                  <span className="text-gray-500">预计耗尽</span>
                  <span>{item.estimated_empty_date}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
