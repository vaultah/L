var gulp = require('gulp'),
    babel = require('gulp-babel'),
    uglify = require('gulp-uglify'),
    sourcemaps = require('gulp-sourcemaps'),
    jshint = require('gulp-jshint'),
    sass = require('gulp-sass'),
    rename = require('gulp-rename'),
    inject = require('gulp-inject');


var CSSDIR = 'dist/public/assets/css',
    CSSPREFIX = Date.now().toString(16) + '-';

gulp.task('js', function() {
    return gulp.src(['src/js/*.js'])
               // .pipe(sourcemaps.init())
               .pipe(jshint({ esnext: true }))
               .pipe(jshint.reporter('default', { verbose: true }))
               .pipe(babel())
               .pipe(uglify())
               // .pipe(sourcemaps.write())
               .pipe(gulp.dest('dist/public/assets/js'));
});


gulp.task('css', function() {
    return gulp.src(['src/css/*.css'])
               .pipe(sass({ outputStyle: 'compressed' }))
               .pipe(rename({ prefix: CSSPREFIX }))
               .pipe(gulp.dest(CSSDIR));
});


gulp.task('markup', ['css'], function() {
    var src = gulp.src([CSSDIR + '/' + CSSPREFIX + '*.css'], { read: false });
    return gulp.src(['src/markup/**/*.html'])
               .pipe(inject(src, { ignorePath: ['dist', 'public'] }))
               .pipe(gulp.dest('dist/markup'));
});


gulp.task('default', ['js', 'css', 'markup']);