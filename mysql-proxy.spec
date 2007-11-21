# TODO
# - initscript probably
#
# Conditional build:
%bcond_without	tests		# build without tests
#
Summary:	MySQL Proxy
Summary(pl.UTF-8):	Proxy MySQL
Name:		mysql-proxy
Version:	0.6.0
Release:	0.1
License:	GPL
Group:		Applications
Source0:	http://mysql.tonnikala.org/Downloads/MySQL-Proxy/%{name}-%{version}.tar.gz
# Source0-md5:	b76ad6f059f78b9aaca49c8c29cb2719
Patch0:		%{name}-lua.patch
URL:		http://forge.mysql.com/wiki/MySQL_Proxy
BuildRequires:	autoconf
BuildRequires:	automake
%{?with_tests:BuildRequires:	check}
BuildRequires:	glib2-devel >= 1:2.4.0
BuildRequires:	libevent-devel
BuildRequires:	lua51-devel
%{?with_tests:BuildRequires:	lua51}
BuildRequires:	mysql-devel
BuildRoot:	%{tmpdir}/%{name}-%{version}-root-%(id -u -n)

%description
MySQL Proxy is a simple program that sits between your client and
MySQL server(s) that can monitor, analyze or transform their
communication. Its flexibility allows for unlimited uses; common ones
include: load balancing; failover; query analysis; query filtering and
modification; and many more.

%description -l pl.UTF-8
MySQL Proxy to prosty program tkwiący między klienten a
serwerem/serwerami MySQL, potrafiący monitorować, analizować i
przekształcać ich komunikację. Jego elastyczność pozwala na
nieograniczone wykorzystanie; popularne sposoby użycia obejmują: load
balancing, failover, analizę zapytań, filtrowanie i modyfikowanie
zapytań... i wiele więcej.

%prep
%setup -q
%patch0 -p1

%build
%{__aclocal} -I m4
%{__autoconf}
%{__autoheader}
%{__automake}
%configure \
	--with-lua=lua51
%{__make}
%{?with_tests:%{__make} check}

%install
rm -rf $RPM_BUILD_ROOT
%{__make} install \
	DESTDIR=$RPM_BUILD_ROOT

# put those to -tutorial package
rm -f $RPM_BUILD_ROOT%{_datadir}/*.lua

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(644,root,root,755)
%doc AUTHORS ChangeLog NEWS README README.TESTS THANKS
%attr(755,root,root) %{_sbindir}/mysql-proxy
%{_datadir}/%{name}
