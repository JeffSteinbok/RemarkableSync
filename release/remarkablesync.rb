class Remarkablesync < Formula
  desc "Backup and convert reMarkable tablet notebooks to PDF"
  homepage "https://github.com/JeffSteinbok/RemarkableSync"
  url "https://github.com/JeffSteinbok/RemarkableSync/archive/refs/tags/v1.0.3.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"
  license "MIT"
  head "https://github.com/JeffSteinbok/RemarkableSync.git", branch: "main"

  depends_on "rust" => :build  # For rmc
  depends_on "python@3.13"
  depends_on "cairo"
  depends_on "pkg-config"

  # Python dependencies
  resource "paramiko" do
    url "https://files.pythonhosted.org/packages/source/p/paramiko/paramiko-3.5.0.tar.gz"
    sha256 "ad11e540da4f55cedda52931f1a3f812a8238a7af7f62a60de538cd80bb28124"
  end

  resource "scp" do
    url "https://files.pythonhosted.org/packages/source/s/scp/scp-0.15.0.tar.gz"
    sha256 "f1b22e9932123ccf17eebf19e0953c6e9148f589f93d91b872941a696305c83f"
  end

  resource "click" do
    url "https://files.pythonhosted.org/packages/source/c/click/click-8.1.8.tar.gz"
    sha256 "ed53c9d8990d83c2a27deae68e4ee337473f6330c040a31d4225c9574d16096a"
  end

  resource "tqdm" do
    url "https://files.pythonhosted.org/packages/source/t/tqdm/tqdm-4.67.1.tar.gz"
    sha256 "f8aef9c52c08c13a65f30ea34f4e5aac3fd1a34959879d7e59e63027286627f2"
  end

  resource "PyPDF2" do
    url "https://files.pythonhosted.org/packages/source/P/PyPDF2/pypdf2-3.0.1.tar.gz"
    sha256 "a74408f69ba6271f71b9352ef4ed03dc53a31aa404d29b5d31f53bfecfee1440"
  end

  resource "reportlab" do
    url "https://files.pythonhosted.org/packages/source/r/reportlab/reportlab-4.2.5.tar.gz"
    sha256 "382ca0a28cf3c1e9e4a2448d6cae5f119498c964b35a0454d1813c1e0e9bf068"
  end

  resource "svglib" do
    url "https://files.pythonhosted.org/packages/source/s/svglib/svglib-1.5.1.tar.gz"
    sha256 "3ae765d3a9409ee60c0fb4d24c2deb6a80853bcbfb49023b834d21dcfdcc5d3f"
  end

  resource "Pillow" do
    url "https://files.pythonhosted.org/packages/source/P/Pillow/pillow-11.0.0.tar.gz"
    sha256 "72bacbaf24ac003fea9bff9837d1eedb6088758d41e100c1552930151f677739"
  end

  resource "rmrl" do
    url "https://files.pythonhosted.org/packages/source/r/rmrl/rmrl-0.2.1.tar.gz"
    sha256 "41e5e7d24b832c9664bb8932da3a69ad842fd59c3485f3f98c4b28aa6bc7a25f"
  end

  def install
    # Install rmc (Rust-based reMarkable converter)
    system "cargo", "install", "--git", "https://github.com/ricklupton/rmc.git", "--root", prefix

    # Install Python dependencies and the main application
    virtualenv_install_with_resources

    # Create a wrapper script that ensures rmc is in PATH
    (bin/"RemarkableSync").write_env_script libexec/"bin/RemarkableSync", PATH: "#{bin}:$PATH"
  end

  test do
    # Test that the command runs and shows help
    assert_match "RemarkableSync", shell_output("#{bin}/RemarkableSync --help")

    # Test that rmc is available
    assert_match "rmc", shell_output("#{bin}/rmc --version")
  end
end
