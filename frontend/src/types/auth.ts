export interface RegisterBody {
  username: string;
  email: string;
  password: string;
}

export interface LoginForm {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
} 