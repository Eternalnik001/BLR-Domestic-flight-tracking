-- Run this ONCE in the Supabase SQL Editor (after the Python job has created the
-- latest / history / watchlist tables on its first run).
--
-- It lets the public anon key (used by the frontend) READ prices and READ/WRITE the
-- watchlist, nothing else. The Python job connects as the table owner and bypasses
-- all of this, so it is unaffected.
--
-- NOTE: anon write to the watchlist means anyone who finds your site URL could edit
-- the tracked routes. That's acceptable for a personal tool. If you later want it
-- locked down, drop the watchlist write policy and add Supabase Auth.

-- 1. Let the API roles reach the public schema + tables.
grant usage on schema public to anon, authenticated;
grant select on public.latest, public.history to anon, authenticated;
grant select, insert, update, delete on public.watchlist to anon, authenticated;

-- 2. Enable row-level security (deny-by-default) on each table.
alter table public.latest    enable row level security;
alter table public.history   enable row level security;
alter table public.watchlist enable row level security;

-- 3. Policies. Prices are read-only to the public; watchlist is fully editable.
drop policy if exists "public read latest"      on public.latest;
drop policy if exists "public read history"     on public.history;
drop policy if exists "public manage watchlist" on public.watchlist;

create policy "public read latest"      on public.latest    for select using (true);
create policy "public read history"     on public.history   for select using (true);
create policy "public manage watchlist" on public.watchlist for all   using (true) with check (true);
