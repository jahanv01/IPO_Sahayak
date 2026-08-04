import { useEffect, useState } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [backendStatus, setBackendStatus] = useState('checking...')

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => res.json())
      .then((data) => setBackendStatus(data.status))
      .catch(() => setBackendStatus('unreachable'))
  }, [])

  return (
    <>
      <h1>IPO Sahayak</h1>
      <p>Hello world — frontend is live.</p>
      <p>
        Backend status: <strong>{backendStatus}</strong>
      </p>
    </>
  )
}

export default App
