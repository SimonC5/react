import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import Header from './components/Header'
import Footer from './components/Footer'
import HomePage from './pages/HomePage'
import AboutPage from './pages/AboutPage'
import ContactPage from './pages/ContactPage'
import Login from './components/Login'
import ResetPassword from './components/ResetPassword'
import ProductsPage from './pages/ProductsPage'
import ServicesPage from './pages/ServicesPage'
import DashboardPage from './pages/DashboardPage'
import WhatsAppButton from './components/WhatsAppButton'
import Chatbot from './components/Chatbot'
import { AuthProvider } from './context/AuthContext'
import { esRutaDePanel } from './utils/rutas'

function ScrollToHash() {
  const location = useLocation();

  useEffect(() => {
    if (!location.hash) {
      window.scrollTo({ top: 0, behavior: 'instant' });
      return;
    }

    const id = location.hash.replace('#', '');
    const element = document.getElementById(id);

    if (element) {
      const headerOffset = 92;
      const top = element.getBoundingClientRect().top + window.scrollY - headerOffset;
      window.scrollTo({ top, behavior: 'smooth' });
    }
  }, [location]);

  return null;
}

function Layout() {
  const { pathname } = useLocation();
  // El panel es un área de trabajo: sin footer ni botón flotante de WhatsApp.
  const enPanel = esRutaDePanel(pathname);

  return (
    <div className="min-h-screen bg-transparent text-slate-100">
      <Header />
      <main className={`mx-auto w-full px-4 py-8 sm:px-6 lg:px-8 ${enPanel ? 'max-w-[110rem]' : 'max-w-7xl'}`}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/productos" element={<ProductsPage />} />
          <Route path="/servicios" element={<ServicesPage />} />
          <Route path="/quienes-somos" element={<AboutPage />} />
          <Route path="/contacto" element={<ContactPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/panel/admin" element={<DashboardPage role="Administrador" />} />
          <Route path="/panel/empleado" element={<DashboardPage role="Empleado" />} />
          <Route path="/panel/cliente" element={<DashboardPage role="Cliente" />} />
        </Routes>
      </main>
      {!enPanel && <Footer />}
      {!enPanel && <WhatsAppButton />}
      <Chatbot />
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <ScrollToHash />
        <Layout />
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
