-- =========================================================
-- ASTRIX V2 — SCHEMA SUPABASE (POSTGRES)
-- Thay thế cho các file JSON trong data/ (guild_settings.json,
-- warnings.json, reminders.json, giveaways.json).
--
-- Cách dùng: mở Supabase Dashboard -> SQL Editor -> dán toàn bộ
-- file này -> Run. Chỉ cần chạy 1 lần khi khởi tạo project.
-- =========================================================

-- ---------------------------------------------------------
-- GUILD SETTINGS
-- Lưu mọi cấu hình theo guild dưới 1 cột JSONB "data", giữ đúng
-- cấu trúc mà utils/data_manager.py cũ đã dùng (log_channel_id,
-- welcome, goodbye, autorole_id, automod, dj_role_id...).
-- ---------------------------------------------------------

create table if not exists guild_settings (
    guild_id    bigint primary key,
    data        jsonb not null default '{}'::jsonb,
    updated_at  timestamptz not null default now()
);

-- ---------------------------------------------------------
-- WARNINGS (CẢNH CÁO)
-- ---------------------------------------------------------

create table if not exists warnings (
    id            bigserial primary key,
    guild_id      bigint not null,
    member_id     bigint not null,
    moderator_id  bigint not null,
    reason        text not null,
    created_at    timestamptz not null default now()
);

create index if not exists idx_warnings_guild_member
    on warnings (guild_id, member_id);

-- ---------------------------------------------------------
-- REMINDERS (NHẮC NHỞ)
-- ---------------------------------------------------------

create table if not exists reminders (
    id          bigserial primary key,
    guild_id    bigint,
    channel_id  bigint not null,
    user_id     bigint not null,
    remind_at   double precision not null,  -- epoch giây, giống time.time()
    message     text not null
);

create index if not exists idx_reminders_remind_at on reminders (remind_at);
create index if not exists idx_reminders_user on reminders (user_id);

-- ---------------------------------------------------------
-- GIVEAWAYS
-- ---------------------------------------------------------

create table if not exists giveaways (
    message_id      bigint primary key,
    guild_id        bigint not null,
    channel_id      bigint not null,
    host_id         bigint not null,
    prize           text not null,
    winners_count   int not null,
    end_time        double precision not null,  -- epoch giây
    participants    bigint[] not null default '{}',
    ended           boolean not null default false
);

create index if not exists idx_giveaways_ended_end_time
    on giveaways (ended, end_time);

-- ---------------------------------------------------------
-- (Tuỳ chọn) Bật Row Level Security nhưng KHÔNG thêm policy nào.
-- Bot dùng SERVICE_ROLE key (bỏ qua RLS hoàn toàn) nên bảng vẫn
-- hoạt động bình thường, đồng thời chặn mọi truy cập từ anon/public
-- key nếu lỡ bị lộ ra frontend nào khác trong tương lai.
-- ---------------------------------------------------------

alter table guild_settings enable row level security;
alter table warnings        enable row level security;
alter table reminders       enable row level security;
alter table giveaways       enable row level security;