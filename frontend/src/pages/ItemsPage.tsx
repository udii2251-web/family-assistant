import { useState, useEffect } from 'react'
import { ShoppingBag, Plus, Edit2, Trash2, Check, X } from 'lucide-react'
import { getItems, getCategories, addItem, updateItem, deleteItem } from '../api'
import type { Item, ItemCategory } from '../types'

export default function ItemsPage() {
  const [items, setItems] = useState<Item[]>([])
  const [categories, setCategories] = useState<ItemCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [addForm, setAddForm] = useState({ name: '', unit: 'kg', target_audience: 'all', category_id: '', typical_size: '' })
  const [editForm, setEditForm] = useState<Partial<Item>>({})

  const load = () => {
    Promise.all([getItems(), getCategories()]).then(([items, cats]) => {
      setItems(items)
      setCategories(cats)
    }).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const audienceLabel = (a: string) => {
    if (a === 'dog') return '宠物'
    if (a === 'child') return '儿童'
    return '全家'
  }

  const handleAdd = async () => {
    if (!addForm.name.trim()) return
    await addItem({
      name: addForm.name,
      unit: addForm.unit,
      target_audience: addForm.target_audience,
      category_id: addForm.category_id ? Number(addForm.category_id) : null,
      typical_size: addForm.typical_size ? Number(addForm.typical_size) : null,
    })
    setShowAdd(false)
    setAddForm({ name: '', unit: 'kg', target_audience: 'all', category_id: '', typical_size: '' })
    load()
  }

  const startEdit = (item: Item) => {
    setEditingId(item.id)
    setEditForm({
      name: item.name,
      unit: item.unit,
      target_audience: item.target_audience,
      category_id: item.category_id,
      typical_size: item.typical_size,
    })
  }

  const saveEdit = async () => {
    if (editingId === null) return
    await updateItem(editingId, editForm)
    setEditingId(null)
    load()
  }

  const handleDelete = async (id: number) => {
    await deleteItem(id)
    load()
  }

  if (loading) return <div className="p-8 text-center text-gray-400">加载中...</div>

  return (
    <div className="p-4 md:p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold">物品管理</h2>
          <p className="text-sm text-gray-500">管理家庭中的所有物品类型</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="bg-blue-500 text-white px-4 py-2 rounded-lg flex items-center gap-1 hover:bg-blue-600">
          <Plus size={16} />添加
        </button>
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="bg-white rounded-xl p-4 border shadow-sm mb-4">
          <h3 className="font-semibold mb-3">添加新物品</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <input placeholder="物品名称" value={addForm.name} onChange={(e) => setAddForm({ ...addForm, name: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" />
            <select value={addForm.unit} onChange={(e) => setAddForm({ ...addForm, unit: e.target.value })} className="border rounded-lg px-3 py-2 text-sm">
              <option value="kg">kg</option><option value="L">L</option><option value="包">包</option>
              <option value="瓶">瓶</option><option value="支">支</option><option value="卷">卷</option><option value="个">个</option>
            </select>
            <select value={addForm.target_audience} onChange={(e) => setAddForm({ ...addForm, target_audience: e.target.value })} className="border rounded-lg px-3 py-2 text-sm">
              <option value="all">全家</option><option value="child">儿童</option><option value="dog">宠物</option>
            </select>
            <select value={addForm.category_id} onChange={(e) => setAddForm({ ...addForm, category_id: e.target.value })} className="border rounded-lg px-3 py-2 text-sm">
              <option value="">选择分类(可选)</option>
              {categories.map(c => <option key={c.id} value={c.id}>{c.icon} {c.name}</option>)}
            </select>
            <input placeholder="常规规格" value={addForm.typical_size} onChange={(e) => setAddForm({ ...addForm, typical_size: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" type="number" />
          </div>
          <div className="flex gap-2 mt-3">
            <button onClick={handleAdd} className="bg-blue-500 text-white px-4 py-1.5 rounded-lg text-sm hover:bg-blue-600">确认</button>
            <button onClick={() => setShowAdd(false)} className="bg-gray-100 text-gray-600 px-4 py-1.5 rounded-lg text-sm hover:bg-gray-200">取消</button>
          </div>
        </div>
      )}

      {/* Items list */}
      <div className="space-y-2">
        {items.map(item => (
          <div key={item.id} className="bg-white rounded-xl p-4 border shadow-sm">
            {editingId === item.id ? (
              <div className="space-y-2">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  <input value={editForm.name ?? ''} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} className="border rounded px-2 py-1 text-sm" />
                  <select value={editForm.unit ?? 'kg'} onChange={(e) => setEditForm({ ...editForm, unit: e.target.value })} className="border rounded px-2 py-1 text-sm">
                    <option value="kg">kg</option><option value="L">L</option><option value="包">包</option>
                    <option value="瓶">瓶</option><option value="支">支</option><option value="卷">卷</option><option value="个">个</option>
                  </select>
                  <select value={editForm.target_audience ?? 'all'} onChange={(e) => setEditForm({ ...editForm, target_audience: e.target.value })} className="border rounded px-2 py-1 text-sm">
                    <option value="all">全家</option><option value="child">儿童</option><option value="dog">宠物</option>
                  </select>
                  <select value={editForm.category_id ?? ''} onChange={(e) => setEditForm({ ...editForm, category_id: e.target.value ? Number(e.target.value) : null })} className="border rounded px-2 py-1 text-sm">
                    <option value="">选择分类</option>
                    {categories.map(c => <option key={c.id} value={c.id}>{c.icon} {c.name}</option>)}
                  </select>
                  <input placeholder="常规规格" value={editForm.typical_size ?? ''} onChange={(e) => setEditForm({ ...editForm, typical_size: e.target.value ? Number(e.target.value) : null })} className="border rounded px-2 py-1 text-sm" type="number" />
                </div>
                <div className="flex gap-2">
                  <button onClick={saveEdit} className="bg-green-500 text-white px-3 py-1 rounded text-xs flex items-center gap-1 hover:bg-green-600"><Check size={14} />保存</button>
                  <button onClick={() => setEditingId(null)} className="bg-gray-100 text-gray-600 px-3 py-1 rounded text-xs flex items-center gap-1 hover:bg-gray-200"><X size={14} />取消</button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 flex-1">
                  <ShoppingBag size={18} className="text-gray-400" />
                  <span className="font-medium">{item.name}</span>
                  <span className="text-xs text-gray-400">{item.unit}</span>
                  {item.typical_size && <span className="text-xs text-gray-400">常规: {item.typical_size}{item.unit}</span>}
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">{audienceLabel(item.target_audience)}</span>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => startEdit(item)} className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded"><Edit2 size={16} /></button>
                  <button onClick={() => handleDelete(item.id)} className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"><Trash2 size={16} /></button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
