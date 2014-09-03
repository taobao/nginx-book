.. nginx_book documentation master file, created by
   sphinx-quickstart on Wed Feb 29 17:58:19 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Nginx开发从入门到精通
=============================


缘起
++++++

nginx由于出色的性能，在世界范围内受到了越来越多人的关注，在淘宝内部它更是被广泛的使用，众多的开发以及运维同学都迫切的想要了解nginx模块的开发以及它的内部原理，但是国内却没有一本关于这方面的书，源于此我们决定自己来写一本。本书的作者为淘宝核心系统服务器平台组的成员，本书写作的思路是从模块开发逐渐过渡到nginx原理剖析。书籍的内容会定期在这里更新，欢迎大家提出宝贵意见，不管是本书的内容问题，还是字词错误，都欢迎大家提交issue(章节标题的左侧有评注按钮)，我们会及时的跟进。

.. topic:: 更新历史

    .. csv-table:: 
       :header: 日期, 描述
       :widths: 20, 160
       :quote: $
       :delim: |

       2012/03/01|创建目录大纲
       2012/03/28|增加了样章
       2012/05/25|更新样章
       2012/06/08|增加第5章
       2012/06/11|增加第4章
       2012/06/26|增加第6章(event module)
       2012/06/27|更新第5章部分内容
       2012/07/04|更新第6章event module部分内容
       2012/07/12|增加第12章（请求头读取，subrequest解析）
       2012/08/14|增加第2章(nginx基础架构及基础概念)
       2012/08/14|增加第2章(ngx_str_t数据结构介绍)
       2012/08/17|增加第7章(模块开发高级篇之变量)
       2012/08/25|增加第11章(nginx的启动阶段部分内容)
       2012/09/26|增加第2章(ngx_array_t,ngx_hash_t及ngx_pool_t介绍)
       2012/10/08|增加第11章(配置解析综述)
       2012/10/12|增加第2章(ngx_hash_wildcard_t,ngx_hash_combined_t及ngx_hash_keys_arrays_t介绍)
       2012/10/21|增加第2章(ngx_chain_t,ngx_list_t及ngx_buf_t介绍)
       2012/11/09|增加第12章(请求体的读取和丢弃解析)
       2012/11/24|更新第2章(ngx_buf_t的部分字段以及其他一些书写错误和表达)
       2012/12/18|更新第11章(解析http块)
       2012/12/10|增加第3章的内容
       2012/12/28|补充和完善了第3章的内容
       2013/01/25|增加了第2章(nginx的配置系统)
       2013/02/18|增加了第2章(nginx的模块化体系结构, nginx的请求处理)
       2013/03/05|增加了第12章部分内容(多阶段请求处理)
       2013/03/08|完成第11章第1节(配置解析综述、ngx_http_block)
       2013/04/16|完成第9章第1节(源码目录结构、configure原理)
       2013/09/30|完成第12章部分内容(多阶段执行链各个阶段解析)
       2013/10/11|完成第12章部分内容(filter解析)
       2013/10/11|完成第12章部分内容(ssl解析)

版权申明
++++++++++++

本书的著作权归作者淘宝核心系统服务器平台组成员所有。你可以：

- 下载、保存以及打印本书
- 网络链接、转载本书的部分或者全部内容，但是必须在明显处提供读者访问本书发布网站的链接
- 在你的程序中任意使用本书所附的程序代码，但是由本书的程序所引起的任何问题，作者不承担任何责任

你不可以：

- 以任何形式出售本书的电子版或者打印版
- 擅自印刷、出版本书
- 以纸媒出版为目的，改写、改编以及摘抄本书的内容

目录
++++++

.. toctree::
   :maxdepth: 4

   module_development.rst
   source_analysis.rst
   appendix_a.rst
   appendix_b.rst
   appendix_c.rst

团队成员
++++++++++++

叔度 (http://blog.zhuzhaoyuan.com)

雕梁 (http://www.pagefault.info)

文景 (http://yaoweibin.cn)

李子 (http://blog.lifeibo.com)

卫越 (http://blog.sina.com.cn/u/1929617884)

袁茁 (http://yzprofile.me)

小熊 (http://dinic.iteye.com)

吉兆 (http://jizhao.blog.chinaunix.net)

静龙 (http://blog.csdn.net/fengmo_q)

竹权 (http://weibo.com/u/2199139545)

公远 (http://100continue.iteye.com/)

布可 (http://weibo.com/sifeierss)

