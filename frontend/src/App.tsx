import { Routes, Route, NavLink } from 'react-router-dom'
import { MessageSquare, Package, Bell, Settings, ShoppingBag } from 'lucide-react'
import ChatPage from './pages/ChatPage'
import InventoryPage from './pages/InventoryPage'
import AlertsPage from './pages/AlertsPage'
import ItemsPage from './pages/ItemsPage'
import SettingsPage from './pages/SettingsPage'

const navItems = [
  { to: '/', icon: MessageSquare, label: '聊天' },
  { to: '/inventory', icon: Package, label: '库存' },
  { to: '/alerts', icon: Bell, label: '提醒' },
  { to: '/items', icon: ShoppingBag, label: '物品' },
  { to: '/settings', icon: Settings, label: '设置' },
]

export default function App() {
  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <nav className="w-16 md:w-56 bg-white border-r flex flex-col py-4">
        <div className="px-4 mb-6 hidden md:block">
          <h1 className="text-lg font-bold text-gray-800">家庭助手</h1>
          <p className="text-xs text-gray-500">4大人 1小孩 2狗狗</p>
        </div>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 text-sm transition-colors ${
                isActive ? 'bg-blue-50 text-blue-600 font-medium' : 'text-gray-600 hover:bg-gray-50'
              }`
            }
          >
            <Icon size={20} />
            <span className="hidden md:inline">{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/inventory" element={<InventoryPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/items" element={<ItemsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}
