import RegisterForm from "../../components/auth/RegisterForm";

const Register = () => {
  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2">

      <div className="hidden lg:flex flex-col justify-center bg-slate-900 text-white p-12">

        <h1 className="text-5xl font-bold">
          Join JobPilot AI
        </h1>

        <p className="mt-6 text-lg text-gray-300">
          Create your account and automate your job search.
        </p>

      </div>

      <div className="flex items-center justify-center bg-gray-50 p-8">

        <RegisterForm />

      </div>

    </div>
  );
};

export default Register;