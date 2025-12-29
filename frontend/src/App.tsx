// String Tension Calculator - React Frontend
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { Summary } from './pages/Summary';
import { Editor } from './pages/Editor';
import './App.css';

function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <div className="app">
          <header className="app-header">
            <h1>String Tension Calculator</h1>
            <nav className="app-nav">
              <NavLink to="/" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                Summary
              </NavLink>
              <NavLink to="/editor" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>
                Editor
              </NavLink>
            </nav>
          </header>
          <main className="app-main">
            <Routes>
              <Route path="/" element={<Summary />} />
              <Route path="/editor" element={<Editor />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </AppProvider>
  );
}

export default App;
