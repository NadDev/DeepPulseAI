import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import Portfolio from './components/Portfolio'
import CryptoList from './components/CryptoList'
import CryptoDetail from './components/CryptoDetail'
import './App.css'

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')

  return (
    <Router>
      <div className="app">
        <nav className="navbar">
          <div className="nav-container">
            <h1 className="logo">
              <span className="logo-icon">₿</span>
              Crypto Portfolio
            </h1>
            <ul className="nav-menu">
              <li>
                <Link
                  to="/"
                  className={currentPage === 'dashboard' ? 'active' : ''}
                  onClick={() => setCurrentPage('dashboard')}
                >
                  Dashboard
                </Link>
              </li>
              <li>
                <Link
                  to="/portfolio"
                  className={currentPage === 'portfolio' ? 'active' : ''}
                  onClick={() => setCurrentPage('portfolio')}
                >
                  Mon Portfolio
                </Link>
              </li>
              <li>
                <Link
                  to="/markets"
                  className={currentPage === 'markets' ? 'active' : ''}
                  onClick={() => setCurrentPage('markets')}
                >
                  Marchés
                </Link>
              </li>
            </ul>
          </div>
        </nav>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/markets" element={<CryptoList />} />
            <Route path="/crypto/:coinId" element={<CryptoDetail />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
