import { Navigate, Route, Routes } from 'react-router-dom'

import Layout from './components/Layout'
import Protected from './components/Protected'
import { useAuth } from './lib/auth'

import Login from './pages/Login'
import Register from './pages/Register'
import MyRFQs from './pages/MyRFQs'
import RFQForm from './pages/RFQForm'
import BuyerRFQDetail from './pages/BuyerRFQDetail'
import BrowseRFQs from './pages/BrowseRFQs'
import SupplierRFQDetail from './pages/SupplierRFQDetail'
import MyQuotations from './pages/MyQuotations'

/** Sends each role to its own home screen. */
function Home() {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={user.role === 'buyer' ? '/buyer/rfqs' : '/browse'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Buyer */}
        <Route
          path="/buyer/rfqs"
          element={
            <Protected role="buyer">
              <MyRFQs />
            </Protected>
          }
        />
        <Route
          path="/buyer/rfqs/new"
          element={
            <Protected role="buyer">
              <RFQForm mode="create" />
            </Protected>
          }
        />
        <Route
          path="/buyer/rfqs/:id"
          element={
            <Protected role="buyer">
              <BuyerRFQDetail />
            </Protected>
          }
        />
        <Route
          path="/buyer/rfqs/:id/edit"
          element={
            <Protected role="buyer">
              <RFQForm mode="edit" />
            </Protected>
          }
        />

        {/* Supplier */}
        <Route
          path="/browse"
          element={
            <Protected role="supplier">
              <BrowseRFQs />
            </Protected>
          }
        />
        <Route
          path="/rfqs/:id"
          element={
            <Protected role="supplier">
              <SupplierRFQDetail />
            </Protected>
          }
        />
        <Route
          path="/my-quotations"
          element={
            <Protected role="supplier">
              <MyQuotations />
            </Protected>
          }
        />

        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}

function NotFound() {
  return (
    <div className="state">
      <h3>Page not found</h3>
      <p className="muted">That page does not exist.</p>
    </div>
  )
}
