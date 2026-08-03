# Đặt file này ở THƯ MỤC GỐC của Repl (ngang hàng với bot.py).
# Nếu Repl đã có sẵn replit.nix, chỉ cần thêm dòng pkgs.ffmpeg
# vào mảng deps hiện có thay vì tạo file mới.

{ pkgs }: {
  deps = [
    pkgs.ffmpeg
    pkgs.libopus
    pkgs.python311
  ];
}
