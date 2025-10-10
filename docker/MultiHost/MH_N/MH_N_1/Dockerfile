FROM php:8.0-apache

# 安装必要的 PHP 扩展
RUN apt-get update && apt-get install -y \
    libpng-dev \
    libjpeg-dev \
    libfreetype6-dev \
    zip \
    unzip \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) gd \
    && docker-php-ext-install mysqli pdo pdo_mysql

# 启用 Apache mod_rewrite
RUN a2enmod rewrite

# 复制自定义 Apache 配置
COPY apache-config.conf /etc/apache2/sites-available/000-default.conf

# 设置工作目录
WORKDIR /var/www/html

# 复制应用代码
COPY dawapharma/dawapharma/dawapharma/ /var/www/html/

# 设置正确的权限
RUN chown -R www-data:www-data /var/www/html/ \
    && chmod -R 755 /var/www/html/


# 暴露端口
EXPOSE 80

# 启动 Apache
CMD ["apache2-foreground"] 