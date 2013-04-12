附录A 编码风格 (100%)
=======================

Nginx代码风格图示 (100%)
---------------------------

一、基本原则

    K&R编码风格（偏BSD子类）。

    每行不能超过80列。

    不用TAB对齐，用空格。

    默认对齐单元是4个空格。

    除宏定义外，字母均为小写，单词间用下划线_间隔。

    使用C方式的注释，不得使用//形式注释。

    中缀运算符的前后须空一格，如3 + 2以及a > 3。

    逗号后须空一格，如foo(a, b, c);

二、风格图示

.. image:: http://tengine.taobao.org/book/_images/code-style-1.JPG

1、	if/while/for/switch语句的左花括号和关键字在同一行上，和括号之间空一个空格。

2、	else关键字和两个花括号在同一行上。

.. image:: http://tengine.taobao.org/book/_images/code-style-2.JPG
   :width: 550px

3、	文件开始的注释空一行。

4、	较为完整的代码块间的距离为空两行。如函数声明、函数定义之间等。

5、	函数声明或定义若一行显示不下，则函数原型空4个空格。

6、	结构体数组的花括号和内容之间空一个空格。

.. image:: http://tengine.taobao.org/book/_images/code-style-3.JPG

7、	结构体数组的左花括号放在同一行上。

8、	较大的结构体数组元素最开始空一行。

9、	元素内容上下对齐。

.. image:: http://tengine.taobao.org/book/_images/code-style-4.JPG

10、注释上下对齐。

.. image:: http://tengine.taobao.org/book/_images/code-style-5.JPG

11、函数调用折行时，参数上下对齐。

.. image:: http://tengine.taobao.org/book/_images/code-style-6.JPG
   :width: 550px

12、函数定义时，类型单独一行。

13、变量声明的类型上下排列按照从短到长的顺序。注意，最下面的变量的类型和名称间的空格为2-3个。一般情况下为2个，这是Nginx中最小的变量声明中类型和名称的距离。

14、变量名称上下对齐——字母对齐，不包括指针的\*号。

.. image:: http://tengine.taobao.org/book/_images/code-style-7.JPG

15、结构体内变量上下对齐（字母，不包括指针的的\*号）。

.. image:: http://tengine.taobao.org/book/_images/code-style-8.JPG
   :width: 550px

16、单行注释格式为/\* something \*/

.. image:: http://tengine.taobao.org/book/_images/code-style-9.JPG
   :width: 550px

17、多行注释的格式为：

.. code:: c

    /*
     * something
     */

.. image:: http://tengine.taobao.org/book/_images/code-style-10.JPG
   :width: 550px

18、函数定义的左花括号独占一行。

19、switch语句中，switch和case关键字上下对齐。

.. image:: http://tengine.taobao.org/book/_images/code-style-11.JPG
   :width: 550px

20、当条件表达式过长需要折行时，关系运算符须位于下一行的行首，并与上一行的条件表达式的第一个字符对齐，同时右花括号须位于单独的一行，并与if/while等关键字对齐。

.. image:: http://tengine.taobao.org/book/_images/code-style-12.JPG
   :width: 550px

21、 else语句之前须空出一行。

.. image:: http://tengine.taobao.org/book/_images/code-style-13.JPG

22、在函数中，相同类型的变量声明放在一行上。
