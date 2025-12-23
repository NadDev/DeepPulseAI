import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import Charts from './components/Charts';
import Portfolio from './components/Portfolio';
import BotManager from './components/BotManager';
import Login from './pages/Login';
import Register from './pages/Register';
import ForgotPassword from './pages/ForgotPassword';
import './App.css';

// Placeholder components for new routes
const Placeholder = ({ title }) => (
  <div className="placeholder-page">
    <h2>{title}</h2>
    <p>Coming soon...</p>
  </div>
);

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public routes - Auth pages */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          
          {/* Protected routes - Main app */}
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <div className="app">
                  <Sidebar />
                  <div className="main-wrapper">
                    <Header />
                    <main className="content">
                      <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/charts" element={<Charts />} />
                        <Route path="/portfolio" element={<Portfolio />} />
                        <Route path="/markets" element={<Placeholder title="Market Analysis" />} />
                        <Route path="/bots" element={<BotManager />} />
                        <Route path="/reports" element={<Placeholder title="Reports & Analytics" />} />
                        <Route path="/risk" element={<Placeholder title="Risk Management" />} />
                        <Route path="/settings" element={<Placeholder title="Settings" />} />
                      </Routes>
                    </main>
                  </div>
                </div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;

