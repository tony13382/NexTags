import { createBrowserRouter } from 'react-router-dom'
import App from './App'
import Home from './pages/Home'
import New from './pages/New'
import Playlists from './pages/Playlists'
import Playlist from './pages/Playlist'
import Cache from './pages/Cache'
import Settings from './pages/Settings'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <Home />,
      },
      {
        path: 'new',
        element: <New />,
      },
      {
        path: 'playlists',
        element: <Playlists />,
      },
      {
        path: 'playlist/:id',
        element: <Playlist />,
      },
      {
        path: 'cache',
        element: <Cache />,
      },
      {
        path: 'settings',
        element: <Settings />,
      },
    ],
  },
])
