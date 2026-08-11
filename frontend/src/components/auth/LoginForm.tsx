import { Link } from "react-router-dom";
import {useForm} from "react-hook-form";

import type {LoginFormData} from "../../types/auth.types";
import { loginSchema } from "../../schemas/auth.schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { authService } from "../../services/auth.service";


const LoginForm = () => {
  const {
    register,
    handleSubmit,
    formState: {errors,isSubmitting}
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema)
  })

  const onSubmit =  async (data:LoginFormData ) => {
      let response = await authService.login(data )
      console.log(response)
  }

  return (
    <div className="w-full max-w-md bg-white rounded-xl shadow-lg p-8">

      <h2 className="text-3xl font-bold text-center">
        Welcome Back
      </h2>

      <p className="text-gray-500 text-center mt-2">
        Login to your account
      </p>

      <form className="mt-8 space-y-5" onSubmit={handleSubmit(onSubmit)}>

        <div>
          <label className="block mb-2 font-medium">
            Email
          </label>

          <input
            placeholder="Enter your email"
            {...register("email")}
            className="w-full border rounded-lg p-3"
          />
          {errors.email && (
            <p>
              {errors.email.message}  
            </p>
          )}

        </div>

        <div>
          <label className="block mb-2 font-medium">
            Password
          </label>

          <input
      
            placeholder="Enter your password"
            {...register("password")}
            className="w-full border rounded-lg p-3"
          />
          {errors.password && (
            <p>
              {errors.password.message}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full bg-blue-600 text-white rounded-lg p-3 hover:bg-blue-700"
        >{
          isSubmitting ?"Signing In..." : "Sign In"
        }
        </button>

      </form>

      <p className="text-center mt-6">

        Don't have an account?

        <Link
          to="/register"
          className="text-blue-600 ml-2"
        >
          Register
        </Link>

      </p>

    </div>
  );
};

export default LoginForm;