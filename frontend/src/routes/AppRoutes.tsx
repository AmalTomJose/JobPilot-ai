import { BrowserRouter,Routes,Route } from "react-router-dom"
import Login from '../pages/Login/Login'
import Dashboard from '../pages/Dashboard/Dashboard'
import Profile from '../pages/Profile/Profile'
import Settings from '../pages/Settings/Settings'
import NotFound from '../pages/NotFound/NotFound'
import Applications from '../pages/Applications/Applications'
import Jobs from '../pages/Jobs/Jobs'
import Register from '../pages/Register/Register'
import Resume from '../pages/Resume/Resume'
import Home from '../pages/Home/Home'

//layout
import MainLayout from "../layouts/MainLayout"
import AuthLayout from "../layouts/AuthLayout"


function AppRoutes() {
  return (
   <BrowserRouter>
  
    <Routes>
      {/* Public */}

        <Route path="/" element={<Home/>}/>

      {/* Authentication */}
        <Route element={<AuthLayout/>}>
            <Route path="/login" element={<Login/>}/>
            <Route path="/register" element={<Register/>}/>
        </Route>
      {/* Protected */}
        <Route element = {<MainLayout/>}>
            <Route path="dashboard" element={<Dashboard/>}/>
            <Route path="profile" element={<Profile/>}/>
            <Route path="settings" element={<Settings/>}/>
            <Route path="applications" element={<Applications/>}/>
            <Route path="jobs" element={<Jobs/>}/>
            <Route path="resume" element={<Resume/>}/>
            
        </Route>  
      {/* 404 */}
        <Route path="*" element={<NotFound/>}/>
    </Routes>


   </BrowserRouter> 
  )
}

export default AppRoutes