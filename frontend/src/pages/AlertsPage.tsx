import { useState, useEffect } from 'react'
import { Bell, Check, Trash2, CheckCircle } from 'lucide-react'
import { getAlerts, updateAlert, getInventory } from '../api'
import type { Alert, InventoryItem } from '../types'

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [inventory, setInventory] = useState<InventoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const load = () => {
    Promise.all([getAlerts(), getInventory()]).then(([alerts, inv]) => {
      setAlerts(alerts)
      setInventory(inv)
    }).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const markDone = async (id: number, itemName: string) => {
    try {
      await updateAlert(id, { status: 'done' })
      setSuccessMessage(`✅ ${itemName} 已标记为补货完成！`)
      setTimeout(() => setSuccessMessage(null), 3000)
      load()
    } catch (e) {
      console.error('Failed to mark done:', e)
      setSuccessMessage('❌ 操作失败，请重试')
      setTimeout(() => setSuccessMessage(null), 3000)
    }
  }

  const getItemName = (itemId: number) => {
    const item = inventory.find(i => i.item_id === itemId)
    return item ? item.item_name : `物品 #${itemId}`
  }

  if (loading) return <div className="p-8 text-center text-gray-400">加载中...</div>

  const pending = alerts.filter(a => a.status === 'pending')
  const notified = alerts.filter(a => a.status === 'notified')
  const done = alerts.filter(a => a.status === 'done')

  return (
    <div className="p-4 md:p-8">
      <h2 className="text-xl font-bold mb-1">补货提醒</h2>
      <p className="text-sm text-gray-500 mb-6">查看和管理所有补货提醒</p>

      {/* Success message toast */}
      {successMessage && (
        <div className="fixed top-4 right-4 bg-green-500 text-white px-4 py-3 rounded-lg shadow-lg z-50 flex items-center gap-2 animate-bounce">
          <CheckCircle size={20} />
          {successMessage}
        </div>
      )}

      {pending.length === 0 && notified.length === 0 && done.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <Bell size={48} className="mx-auto mb-4 opacity-50" />
          <p>暂无补货提醒，一切正常！</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Pending */}
          {pending.length > 0 && (
            <section>
              <h3 className="font-semibold text-red-700 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-red-500 rounded-full" />
                待处理 ({pending.length})
              </h3>
              <div className="space-y-2">
                {pending.map(alert => (
                  <div key={alert.id} className="bg-white rounded-xl p-4 border border-red-200 shadow-sm">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <span className="font-semibold">{getItemName(alert.item_id)}</span>
                        <p className="text-sm text-gray-600 mt-1">{alert.message}</p>
                        {alert.estimated_empty_date && (
                          <p className="text-xs text-gray-400 mt-1">预计耗尽：{alert.estimated_empty_date}</p>
                        )}
                        {alert.suggested_quantity && (
                          <p className="text-xs text-gray-400">建议补货量：{alert.suggested_quantity}</p>
                        )}
                      </div>
                      <button onClick={() => markDone(alert.id, getItemName(alert.item_id))} className="bg-green-500 text-white px-3 py-1.5 rounded-lg text-sm flex items-center gap-1 hover:bg-green-600 transition-all hover:scale-105">
                        <Check size={14} />已补货
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Notified */}
          {notified.length > 0 && (
            <section>
              <h3 className="font-semibold text-yellow-700 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-yellow-500 rounded-full" />
                已通知 ({notified.length})
              </h3>
              <div className="space-y-2">
                {notified.map(alert => (
                  <div key={alert.id} className="bg-white rounded-xl p-4 border border-yellow-200 shadow-sm">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <span className="font-semibold">{getItemName(alert.item_id)}</span>
                        <p className="text-sm text-gray-600 mt-1">{alert.message}</p>
                      </div>
                      <button onClick={() => markDone(alert.id, getItemName(alert.item_id))} className="bg-green-500 text-white px-3 py-1.5 rounded-lg text-sm flex items-center gap-1 hover:bg-green-600 transition-all hover:scale-105">
                        <Check size={14} />已补货
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Done */}
          {done.length > 0 && (
            <section>
              <h3 className="font-semibold text-green-700 mb-3 flex items-center gap-2">
                <CheckCircle size={18} />
                已完成 ({done.length})
              </h3>
              <div className="space-y-2">
                {done.map(alert => (
                  <div key={alert.id} className="bg-green-50 rounded-xl p-4 border border-green-200 shadow-sm">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <CheckCircle className="text-green-500" size={20} />
                        <span className="font-semibold text-green-900">{getItemName(alert.item_id)}</span>
                      </div>
                      <span className="text-xs text-gray-400">{alert.alert_date}</span>
                    </div>
                    <p className="text-sm text-green-700 mt-1 ml-7">{alert.message}</p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
