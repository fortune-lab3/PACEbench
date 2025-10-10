FROM php:7.4-apache

# 安装 mysqli 扩展
RUN docker-php-ext-install mysqli && docker-php-ext-enable mysqli

# 拷贝源码到网站目录
COPY . /var/www/html/

# 启用 Apache mod_rewrite
RUN a2enmod rewrite

# 设置工作目录权限
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80

CMD ["apache2-foreground"] 