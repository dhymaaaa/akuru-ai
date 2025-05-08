import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './lib/auth-context';
// import ProtectedRoute from './components/ProtectedRoute';
import { Login } from './pages/Auth/Login';
import SignUp from './pages/Auth/SignUp';
import './App.css';
import Home from './pages/Home';

// Import your other components/pages
// import Dashboard from './pages/Dashboard';
// import Home from './pages/Home';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/try" element={<div>Try it first page</div>} />
          
          {/* Protected routes */}
          {/* <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <div>Dashboard (Protected Route)</div>
              </ProtectedRoute>
            } 
          /> */}

          {/* Default route - redirect to login */}
          <Route path="/" element={<Navigate to="/login" replace />} />
          
          {/* Catch-all route for 404 */}
          <Route path="*" element={<div>Page not found</div>} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;