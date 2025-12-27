import { Outlet } from 'react-router-dom'
import Navbar from '@/components/Navbar'
import { Toaster } from '@/components/ui/sonner'

export default function App() {
  return (
    <div className="bg-gray-50 min-h-screen">
      <Navbar />
      <main className="mx-auto">
        <Outlet />
      </main>
      <Toaster />
    </div>
  )
}
