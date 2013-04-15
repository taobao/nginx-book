nginx架构详解
===========================
nginx的下篇将会更加深入的介绍nginx的实现原理。上一章，我们了解到了如何设计一个高性能服务器，那这一章将会开始讲解，nginx是如何一步一步实现高性能服务器的。



nginx的源码目录结构
------------------------------

nginx的优秀除了体现在程序结构以及代码风格上，nginx的源码组织也同样简洁明了，目录结构层次结构清晰，值得我们去学习。nginx的源码目录与nginx的模块化以及功能的划分是紧密结合，这也使得我们可以很方便地找到相关功能的代码。这节先介绍nginx源码的目录结构，先对nginx的源码有一个大致的认识，下节会讲解nginx如何编译。
下面是nginx源码的目录结构：

.
├── auto            自动检测系统环境以及编译相关的脚本

│   ├── cc          关于编译器相关的编译选项的检测脚本
│   ├── lib         nginx编译所需要的一些库的检测脚本
│   ├── os          与平台相关的一些系统参数与系统调用相关的检测
│   └── types       与数据类型相关的一些辅助脚本
├── conf            存放默认配置文件，在make install后，会拷贝到安装目录中去
├── contrib         存放一些实用工具，如geo配置生成工具（geo2nginx.pl）
├── html            存放默认的网页文件，在make install后，会拷贝到安装目录中去
├── man             nginx的man手册
└── src             存放nginx的源代码
    ├── core        nginx的核心源代码，包括常用数据结构的定义，以及nginx初始化运行的核心代码如main函数
    ├── event       对系统事件处理机制的封装，以及定时器的实现相关代码
    │   └── modules 不同事件处理方式的模块化，如select、poll、epoll、kqueue等
    ├── http        nginx作为http服务器相关的代码
    │   └── modules 包含http的各种功能模块
    ├── mail        nginx作为邮件代理服务器相关的代码
    ├── misc        一些辅助代码，测试c++头的兼容性，以及对google_perftools的支持
    └── os          主要是对各种不同体系统结构所提供的系统函数的封装，对外提供统一的系统调用接口



nginx的configure原理
---------------------------
nginx的编译旅程将从configure开始，configure脚本将根据我们输入的选项、系统环境参与来生成所需的文件（包含源文件与Makefile文件）。configure会调用一系列auto脚本来实现编译环境的初始化。



auto脚本
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

auto脚本由一系列脚本组成，他们有一些是实现一些通用功能由其它脚本来调用（如have），有一些则是完成一些特定的功能（如option）。脚本之间的主要执行顺序及调用关系如下图所示（由上到下，表示主流程的执行）：

.. image:: http://tengine.taobao.org/book/_images/chapter-9-1.png

接下来，我们结合代码来分析下configure的原理:

1)
.. code:: c

    . auto/options
    . auto/init
    . auto/sources

这是configure源码开始执行的前三行，依次交由auto目录下面的option、init、sources来处理。

2)
auto/options主是处理用户输入的configure选项，以及输出帮助信息等。读者可以结合nginx的源码来阅读本章内容。由于篇幅关系，这里大致列出此文件的结构：

.. code:: c
    ##1. 设置选项对应的shell变量以及他们的初始值
    help=no
    NGX_PREFIX=
    NGX_SBIN_PATH=
    NGX_CONF_PREFIX=
    NGX_CONF_PATH=
    NGX_ERROR_LOG_PATH=
    NGX_PID_PATH=
    NGX_LOCK_PATH=
    NGX_USER=
    NGX_GROUP=

    ...


    ## 2, 处理每一个选项值，并设置到对应的全局变量中
    for option
    do
        opt="$opt `echo $option | sed -e \"s/\(--[^=]*=\)\(.* .*\)/\1'\2'/\"`"

        # 得到此选项的value部分
        case "$option" in
            -*=*) value=`echo "$option" | sed -e 's/[-_a-zA-Z0-9]*=//'` ;;
                *) value="" ;;
        esac

        # 根据option内容进行匹配，并设置相应的选项
        case "$option" in
            --help)                          help=yes                   ;;
            --prefix=)                       NGX_PREFIX="!"             ;;
            --prefix=*)                      NGX_PREFIX="$value"        ;;
            --sbin-path=*)                   NGX_SBIN_PATH="$value"     ;;
            --conf-path=*)                   NGX_CONF_PATH="$value"     ;;
            --error-log-path=*)              NGX_ERROR_LOG_PATH="$value";;
            --pid-path=*)                    NGX_PID_PATH="$value"      ;;
            --lock-path=*)                   NGX_LOCK_PATH="$value"     ;;
            --user=*)                        NGX_USER="$value"          ;;
            --group=*)                       NGX_GROUP="$value"         ;;

            ...

            *)
                # 没有找到的对应选项
                echo "$0: error: invalid option \"$option\""
                exit 1
            ;;
        esac
    done

    ## 3. 对选项进行处理

    # 如果有--help，则输出帮助信息
    if [ $help = yes ]; then

        cat << END

            --help                             print this message

            --prefix=PATH                      set installation prefix
            --sbin-path=PATH                   set nginx binary pathname
            --conf-path=PATH                   set nginx.conf pathname
            --error-log-path=PATH              set error log pathname
            --pid-path=PATH                    set nginx.pid pathname
            --lock-path=PATH                   set nginx.lock pathname

            --user=USER                        set non-privileged user for
            worker processes
            --group=GROUP                      set non-privileged group for
                                     worker processes
    END

        exit 1
    fi

    # 默认文件路径
    NGX_CONF_PATH=${NGX_CONF_PATH:-conf/nginx.conf}
    NGX_CONF_PREFIX=`dirname $NGX_CONF_PATH`
    NGX_PID_PATH=${NGX_PID_PATH:-logs/nginx.pid}
    NGX_LOCK_PATH=${NGX_LOCK_PATH:-logs/nginx.lock}

    ...

上面的代码中，我们选用了文件中的部分代码进行了说明。大家可结合源码再进行分析。auto/options的目的主要是处理用户选项，并由选项生成一些全局变量的值，这些值在其它文件中会用到。该文件也会输出configure的帮助信息。

3) auto/init
该文件的目录在于初始化一些临时文件的路径，检查echo的兼容性，并创建Makefile。

.. code:: c
    # 生成最终执行编译的makefile文件路径
    NGX_MAKEFILE=$NGX_OBJS/Makefile
    # 动态生成nginx模块列表的路径，由于nginx的的一些模块是可以选择编译的，而且可以添加自己的模块，所以模块列表是动态生成的
    NGX_MODULES_C=$NGX_OBJS/ngx_modules.c

    NGX_AUTO_HEADERS_H=$NGX_OBJS/ngx_auto_headers.h
    NGX_AUTO_CONFIG_H=$NGX_OBJS/ngx_auto_config.h

    # 自动测试目录与日志输出文件
    NGX_AUTOTEST=$NGX_OBJS/autotest
    # 如果configure出错，可用来查找出错的原因
    NGX_AUTOCONF_ERR=$NGX_OBJS/autoconf.err

    NGX_ERR=$NGX_OBJS/autoconf.err
    MAKEFILE=$NGX_OBJS/Makefile


    NGX_PCH=
    NGX_USE_PCH=


    # 检查echo是否支持-n或\c

    # check the echo's "-n" option and "\c" capability

    if echo "test\c" | grep c >/dev/null; then

        # 不支持-c的方式，检查是否支持-n的方式

        if echo -n test | grep n >/dev/null; then
            ngx_n=
            ngx_c=

        else
            ngx_n=-n
            ngx_c=
        fi

    else
        ngx_n=
        ngx_c='\c'
    fi

    # 创建最初始的makefile文件
    # default表示目前编译对象
    # clean表示执行clean工作时，需要删除makefile文件以及objs目录
    # 整个过程中只会生成makefile文件以及objs目录，其它所有临时文件都在objs目录之下，所以执行clean后，整个目录还原到初始状态
    # 要再次执行编译，需要重新执行configure命令

    # create Makefile

    cat << END > Makefile

    default:    build

    clean:
        rm -rf Makefile $NGX_OBJS
    END

4) auto/sources
该文件从文件名中就可以看出，它的主要功能是跟源文件相关的。它的主要作用是定义不同功能或系统所需要的文件的变量。根据功能，分为CORE/REGEX/EVENT/UNIX/FREEBSD/HTTP等。每一个功能将会由四个变量组成，"_MODULES"表示此功能相关的模块，最终会输出到ngx_modules.c文件中，即动态生成需要编译到nginx中的模块；"INCS"表示此功能依赖的源码目录，查找头文件的时候会用到，在编译选项中，会出现在"-I"中；”DEPS"显示指明在Makefile中需要依赖的文件名，即编译时，需要检查这些文件的更新时间；"SRCS"表示需要此功能编译需要的源文件。

拿core来说：

.. code:: c
    CORE_MODULES="ngx_core_module ngx_errlog_module ngx_conf_module ngx_emp_server_module ngx_emp_server_core_module"

    CORE_INCS="src/core"

    CORE_DEPS="src/core/nginx.h \
             src/core/ngx_config.h \
             src/core/ngx_core.h \
             src/core/ngx_log.h \
             src/core/ngx_palloc.h \
             src/core/ngx_array.h \
             src/core/ngx_list.h \
             src/core/ngx_hash.h \
             src/core/ngx_buf.h \
             src/core/ngx_queue.h \
             src/core/ngx_string.h \
             src/core/ngx_parse.h \
             src/core/ngx_inet.h \
             src/core/ngx_file.h \
             src/core/ngx_crc.h \
             src/core/ngx_crc32.h \
             src/core/ngx_murmurhash.h \
             src/core/ngx_md5.h \
             src/core/ngx_sha1.h \
             src/core/ngx_rbtree.h \
             src/core/ngx_radix_tree.h \
             src/core/ngx_slab.h \
             src/core/ngx_times.h \
             src/core/ngx_shmtx.h \
             src/core/ngx_connection.h \
             src/core/ngx_cycle.h \
             src/core/ngx_conf_file.h \
             src/core/ngx_resolver.h \
             src/core/ngx_open_file_cache.h \
             src/core/nginx_emp_server.h \
             src/core/emp_server.h \
             src/core/task_thread.h \
             src/core/standard.h \
             src/core/dprint.h \
             src/core/ngx_crypt.h"

    CORE_SRCS="src/core/nginx.c \
             src/core/ngx_log.c \
             src/core/ngx_palloc.c \
             src/core/ngx_array.c \
             src/core/ngx_list.c \
             src/core/ngx_hash.c \
             src/core/ngx_buf.c \
             src/core/ngx_queue.c \
             src/core/ngx_output_chain.c \
             src/core/ngx_string.c \
             src/core/ngx_parse.c \
             src/core/ngx_inet.c \
             src/core/ngx_file.c \
             src/core/ngx_crc32.c \
             src/core/ngx_murmurhash.c \
             src/core/ngx_md5.c \
             src/core/ngx_rbtree.c \
             src/core/ngx_radix_tree.c \
             src/core/ngx_slab.c \
             src/core/ngx_times.c \
             src/core/ngx_shmtx.c \
             src/core/ngx_connection.c \
             src/core/ngx_cycle.c \
             src/core/ngx_spinlock.c \
             src/core/ngx_cpuinfo.c \
             src/core/ngx_conf_file.c \
             src/core/ngx_resolver.c \
             src/core/ngx_open_file_cache.c \
             src/core/nginx_emp_server.c \
             src/core/emp_server.c \
             src/core/standard.c \
             src/core/task_thread.c \
             src/core/dprint.c \
             src/core/ngx_crypt.c"

如果我们自己写一个第三方模块，我们可能会引用到这些变量的值，或对这些变量进行修改，比如添加我们自己的模块，或添加自己的一个头文件查找目录(在第三方模块的config中)，在后面，我们会看到它是如何加框第三方模块的。
在继续分析执行流程之前，我们先介绍一些工具脚本。

5) auto/have

.. code:: c

    cat << END >> $NGX_AUTO_CONFIG_H

    #ifndef $have
    #define $have  1
    #endif

    END

从代码中，我们可以看到，这个工具的作用是，将$have变量的值，宏定义为1，并输出到auto_config文件中。通常我们通过这个工具来控制是否打开某个特性。这个工具在使用前，需要先定义宏的名称 ，即$have变量。

6)



模块编译顺序
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



nginx的事件机制
------------------------



event框架及非阻塞模型
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



定时器实现
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



信号处理
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



惊群问题
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



nginx的进程机制
------------------------



master进程
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



worker进程
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



进程间通讯
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



