# TODO
# - initscript probably
Summary:	MySQL Proxy
Name:		mysql-proxy
Version:	0.5.0
Release:	0.1
License:	GPL
Group:		Applications
Source0:	http://mysql.tonnikala.org/Downloads/MySQL-Proxy/%{name}-%{version}.tar.gz
# Source0-md5:	f97aefed2fddd2353343a716d9c646c6
URL:		http://forge.mysql.com/wiki/MySQL_Proxy
BuildRequires:	glib2-devel >= 1:2.4.0
BuildRequires:	libevent-devel
BuildRequires:	lua51-devel
BuildRequires:	mysql-devel
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%description
MySQL Proxy is a simple program that sits between your client and
MySQL server(s) that can monitor, analyze or transform their
communication. Its flexibility allows for unlimited uses; common ones
include: load balancing; failover; query analysis; query filtering and
modification; and many more.

%prep
%setup -q -n %{name}-%{version}r8

%build
%configure \
	--with-lua=lua51
%{__make}

%install
rm -rf $RPM_BUILD_ROOT
%{__make} install \
	DESTDIR=$RPM_BUILD_ROOT

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(644,root,root,755)
%doc AUTHORS ChangeLog NEWS README THANKS
%attr(755,root,root) %{_sbindir}/mysql-proxy
