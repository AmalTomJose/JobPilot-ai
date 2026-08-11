import LoginForm from "../../components/auth/LoginForm";

const Login = () => {
  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2">
      {/* Left Side */}
      <div className="hidden lg:flex flex-col justify-center bg-slate-900 text-white p-12">
        <h1 className="text-5xl font-bold">JobPilot AI</h1>

        <p className="mt-6 text-lg text-gray-300">
          AI-powered job search and application platform.
        </p>

        <div className="mt-10 space-y-3">
          <p>✔ AI Resume Analysis</p>
          <p>✔ Smart Job Matching</p>
          <p>✔ One Click Apply</p>
          <p>✔ Application Tracking</p>
        </div>
      </div>

      {/* Right Side */}
      <div className="flex items-center justify-center bg-gray-50 p-8">
        <LoginForm />
      </div>
    </div>
  );
};

export default Login;