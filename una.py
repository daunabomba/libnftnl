import subprocess
import os
import multiprocessing
import shutil
from pathlib import Path
from mods import colors
from mods.build import get_build_env

def target_configure(staging_dir: Path, target_dir: Path, arch="x32"):
    colors.info(f"libnftnl: target_configure ({arch})")
    repo_root = Path(__file__).parent
    
    # Generate configure script if it doesn't exist
    if not (repo_root / "configure").exists():
        colors.info("libnftnl: running autoreconf...")
        subprocess.run(["autoreconf", "-fi"], cwd=repo_root, env=get_build_env(staging_dir), check=True)

    std_flags = os.environ.get("CFLAGS", "")
    static_flags = os.environ.get("CFLAGS_STATIC", std_flags)
    
    host_triple = {
        "x32": "x86_64-linux-muslx32",
        "x86_64": "x86_64-linux-musl",
        "aarch64": "aarch64-linux-musl",
        "riscv64": "riscv64-linux-musl",
    }.get(arch, "x86_64-linux-musl")

    cmd = [
        "./configure",
        f"--host={host_triple}",
        "--prefix=/usr",
        "--enable-static",
        "--without-doxygen",
        f"CC=clang {std_flags}",
        f"LDFLAGS={static_flags}",
    ]
    
    subprocess.run(cmd, cwd=repo_root, env=get_build_env(staging_dir), check=True)

def target_build(staging_dir: Path, target_dir: Path, arch="x32"):
    colors.info(f"libnftnl: target_build")
    repo_root = Path(__file__).parent
    make_jobs = multiprocessing.cpu_count()
    subprocess.run(["make", f"-j{make_jobs}"], cwd=repo_root, env=get_build_env(staging_dir), check=True)

def target_install(staging_dir: Path, target_dir: Path, arch="x32"):
    colors.info(f"libnftnl: target_install")
    repo_root = Path(__file__).parent
    
    # Install to staging for use by nftables
    colors.info(f"libnftnl: installing to staging {staging_dir}")
    subprocess.run(["make", f"DESTDIR={staging_dir}", "install"], cwd=repo_root, env=get_build_env(staging_dir), check=True)
    
    # Install to target for runtime
    colors.info(f"libnftnl: installing to target {target_dir}")
    subprocess.run(["make", f"DESTDIR={target_dir}", "install"], cwd=repo_root, env=get_build_env(staging_dir), check=True)

    # Prune development files and documentation from target
    colors.info(f"libnftnl: pruning development files and documentation from target...")
    shutil.rmtree(target_dir / "usr" / "include", ignore_errors=True)
    shutil.rmtree(target_dir / "usr" / "share" / "man", ignore_errors=True)
    shutil.rmtree(target_dir / "usr" / "lib" / "pkgconfig", ignore_errors=True)
    
    # Prune .la files from staging and target
    for la in (staging_dir / "usr" / "lib").glob("*.la"):
        la.unlink()
    for la in (target_dir / "usr" / "lib").glob("*.la"):
        la.unlink()

    # Remove static libs from target
    for lib in (target_dir / "usr" / "lib").glob("*.a"):
        lib.unlink()
