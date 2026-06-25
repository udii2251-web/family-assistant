import { useState, useEffect } from 'react'
import { Users, Edit2, Trash2, Plus, Check, X } from 'lucide-react'
import { getFamily, addMember, updateMember, deleteMember } from '../api'
import type { FamilyMember } from '../types'

export default function SettingsPage() {
  const [members, setMembers] = useState<FamilyMember[]>([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState({ name: '', type: 'adult', age: '', weight: '', breed: '' })
  const [editForm, setEditForm] = useState<Partial<FamilyMember>>({})

  const load = () => {
    getFamily().then(setMembers).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const typeLabel = (t: string) => {
    if (t === 'adult') return '大人'
    if (t === 'child') return '小孩'
    if (t === 'dog') return '小狗'
    return t
  }

  const startEdit = (m: FamilyMember) => {
    setEditingId(m.id)
    setEditForm({ name: m.name, age: m.age, weight: m.weight, breed: m.breed })
  }

  const saveEdit = async () => {
    if (editingId === null) return
    const data: Record<string, unknown> = {}
    if (editForm.name !== undefined) data.name = editForm.name
    if (editForm.age !== undefined) data.age = editForm.age
    if (editForm.weight !== undefined) data.weight = editForm.weight
    if (editForm.breed !== undefined) data.breed = editForm.breed
    await updateMember(editingId, data)
    setEditingId(null)
    load()
  }

  const handleAdd = async () => {
    if (!addForm.name.trim()) return
    await addMember({
      name: addForm.name,
      type: addForm.type,
      age: addForm.age ? Number(addForm.age) : null,
      weight: addForm.weight ? Number(addForm.weight) : null,
      breed: addForm.breed || null,
    })
    setShowAdd(false)
    setAddForm({ name: '', type: 'adult', age: '', weight: '', breed: '' })
    load()
  }

  const handleDelete = async (id: number) => {
    await deleteMember(id)
    load()
  }

  if (loading) return <div className="p-8 text-center text-gray-400">加载中...</div>

  return (
    <div className="p-4 md:p-8 max-w-2xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold">家庭设置</h2>
          <p className="text-sm text-gray-500">查看和管理家庭成员信息</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="bg-blue-500 text-white px-4 py-2 rounded-lg flex items-center gap-1 hover:bg-blue-600"
        >
          <Plus size={16} />
          添加成员
        </button>
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="bg-white rounded-xl p-4 border shadow-sm mb-4">
          <h3 className="font-semibold mb-3">添加家庭成员</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <input placeholder="姓名" value={addForm.name} onChange={(e) => setAddForm({ ...addForm, name: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" />
            <select value={addForm.type} onChange={(e) => setAddForm({ ...addForm, type: e.target.value })} className="border rounded-lg px-3 py-2 text-sm">
              <option value="adult">大人</option>
              <option value="child">小孩</option>
              <option value="dog">小狗</option>
            </select>
            <input placeholder="年龄" value={addForm.age} onChange={(e) => setAddForm({ ...addForm, age: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" type="number" />
            <input placeholder="体重(kg)" value={addForm.weight} onChange={(e) => setAddForm({ ...addForm, weight: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" type="number" />
            {addForm.type === 'dog' && (
              <input placeholder="品种" value={addForm.breed} onChange={(e) => setAddForm({ ...addForm, breed: e.target.value })} className="border rounded-lg px-3 py-2 text-sm" />
            )}
          </div>
          <div className="flex gap-2 mt-3">
            <button onClick={handleAdd} className="bg-blue-500 text-white px-4 py-1.5 rounded-lg text-sm hover:bg-blue-600">确认</button>
            <button onClick={() => setShowAdd(false)} className="bg-gray-100 text-gray-600 px-4 py-1.5 rounded-lg text-sm hover:bg-gray-200">取消</button>
          </div>
        </div>
      )}

      {/* Member list */}
      <div className="bg-white rounded-xl p-4 border shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Users size={20} className="text-gray-400" />
          <h3 className="font-semibold">家庭成员</h3>
        </div>
        <div className="space-y-2">
          {members.map(member => (
            <div key={member.id} className="border rounded-lg p-3">
              {editingId === member.id ? (
                /* Edit mode */
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <input value={editForm.name ?? ''} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} className="border rounded px-2 py-1 text-sm" />
                    <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full w-fit">{typeLabel(member.type)}</span>
                    <input placeholder="年龄" value={editForm.age ?? ''} onChange={(e) => setEditForm({ ...editForm, age: e.target.value ? Number(e.target.value) : null })} className="border rounded px-2 py-1 text-sm" type="number" />
                    <input placeholder="体重(kg)" value={editForm.weight ?? ''} onChange={(e) => setEditForm({ ...editForm, weight: e.target.value ? Number(e.target.value) : null })} className="border rounded px-2 py-1 text-sm" type="number" />
                    {member.type === 'dog' && (
                      <input placeholder="品种" value={editForm.breed ?? ''} onChange={(e) => setEditForm({ ...editForm, breed: e.target.value })} className="border rounded px-2 py-1 text-sm" />
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button onClick={saveEdit} className="bg-green-500 text-white px-3 py-1 rounded text-xs flex items-center gap-1 hover:bg-green-600"><Check size={14} />保存</button>
                    <button onClick={() => setEditingId(null)} className="bg-gray-100 text-gray-600 px-3 py-1 rounded text-xs flex items-center gap-1 hover:bg-gray-200"><X size={14} />取消</button>
                  </div>
                </div>
              ) : (
                /* Display mode */
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 flex-1">
                    <span className="font-medium">{member.name}</span>
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full">{typeLabel(member.type)}</span>
                    {member.age !== null && <span className="text-sm text-gray-500">{member.age}岁</span>}
                    {member.weight !== null && <span className="text-sm text-gray-500">{member.weight}kg</span>}
                    {member.breed && <span className="text-sm text-gray-500">{member.breed}</span>}
                  </div>
                  <div className="flex items-center gap-1">
                    <button onClick={() => startEdit(member)} className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded"><Edit2 size={16} /></button>
                    <button onClick={() => handleDelete(member.id)} className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"><Trash2 size={16} /></button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="mt-4 pt-3 border-t text-sm text-gray-500">
          共 {members.length} 位成员：{members.filter(m => m.type === 'adult').length} 大人、{members.filter(m => m.type === 'child').length} 小孩、{members.filter(m => m.type === 'dog').length} 小狗
        </div>
      </div>
    </div>
  )
}
