import { lazy } from 'react';
import { createBrowserRouter, createRoutesFromElements, RouterProvider, Route } from "react-router-dom";
import ResumeReview from '../pages/ResumeReview/ResumeReview';
import Login from '../pages/Login/Login';
import Dashboard from '../pages/Dashboard/Dashboard';
import Profile from '../pages/Profile/Profile';
import Settings from '../pages/Settings/Settings';
import NotFound from '../pages/NotFound/NotFound';
import Applications from '../pages/Applications/Applications';
const JobIntake = lazy(() => import('../pages/Jobs/JobIntake'));
const JobReview = lazy(() => import('../pages/Jobs/JobReview'));
const JobDetail = lazy(() => import('../pages/Jobs/JobDetail'));
const JobEditor = lazy(() => import('../components/Jobs/JobEditor'));
const Matches = lazy(() => import('../pages/Matches/Matches'));
const Jobs = lazy(() => import('../pages/Jobs/Jobs'));
import Register from '../pages/Register/Register';
import Resume from '../pages/Resume/Resume';
import Home from '../pages/Home/Home';
//layout
import MainLayout from "../layouts/MainLayout";
import AuthLayout from "../layouts/AuthLayout";
//protecedRoute
import ProtectedRoute from "./ProtectedRoute";
const router = createBrowserRouter(createRoutesFromElements(<>
      {/* Public */}

        <Route path="/" element={<Home />}/>

      {/* Authentication */}
        <Route element={<AuthLayout />}>
            <Route path="/login" element={<Login />}/>
            <Route path="/register" element={<Register />}/>
        </Route>
      {/* Protected */}
      <Route element={<ProtectedRoute />}>
        <Route element={<MainLayout />}>
            <Route path="dashboard" element={<Dashboard />}/>
            <Route path="profile" element={<Profile />}/>
            <Route path="settings" element={<Settings />}/>
            <Route path="applications" element={<Applications />}/>
            <Route path="matches" element={<Matches />}/>
            <Route path="jobs" element={<Jobs />}/>
            <Route path="jobs/new" element={<JobEditor/>}/>
            <Route path="jobs/import" element={<JobIntake/>}/>
            <Route path="jobs/imports/:importId/review" element={<JobReview/>}/>
            <Route path="jobs/:jobId" element={<JobDetail/>}/>
            <Route path="jobs/:jobId/edit" element={<JobReview editing/>}/>
            <Route path="resume" element={<Resume />}/>
            <Route path="resume/:resumeId/review" element={<ResumeReview />}/>
            
        </Route>  
      </Route>
      {/* 404 */}
        <Route path="*" element={<NotFound />}/>
</>));
function AppRoutes() { return <RouterProvider router={router}/>; }
export default AppRoutes;
