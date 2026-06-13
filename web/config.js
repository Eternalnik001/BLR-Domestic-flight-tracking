// Frontend config. These two values are SAFE to commit and expose publicly:
// the anon key only grants what your Supabase Row-Level-Security policies allow
// (see web/supabase_setup.sql). It is NOT the database password and NOT a secret.
//
// Fill both in:
//   1. SUPABASE_URL  -> Supabase dashboard -> Project Settings -> API -> Project URL
//   2. SUPABASE_ANON_KEY -> same page -> Project API keys -> "anon public"
window.CONFIG = {
  SUPABASE_URL: "https://piiysbdqxkioznewcszl.supabase.co",
  SUPABASE_ANON_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBpaXlzYmRxeGtpb3puZXdjc3psIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEzMzc4NDYsImV4cCI6MjA5NjkxMzg0Nn0.qtq99je4Y9WDo-QfVVFGKGprYpOjmpZZKuu0ckmG46A",
  ORIGIN: "BLR",
};
