var gulp = require('gulp'),
    babel = require('gulp-babel'),
    uglify = require('gulp-uglify'),
    sourcemaps = require('gulp-sourcemaps'),
    jshint = require('gulp-jshint'),
    sass = require('gulp-sass'),
    rename = require("gulp-rename");


gulp.task('js', function() {
    return gulp.src(['src/js/*.js'])
               // .pipe(sourcemaps.init())
               .pipe(jshint({ esnext: true }))
			         .pipe(jshint.reporter('default', { verbose: true }))
               .pipe(babel())
               .pipe(uglify())
               // .pipe(sourcemaps.write())
               .pipe(gulp.dest('public/assets/js'));
});


gulp.task('css', function () {
    return gulp.src(['src/js/*.css'])
               .pipe(sass({ style: 'compressed' }))
               .pipe(rename({ suffix: '.min' }))
               .pipe(gulp.dest('public/assets/css'));
});


gulp.task('default', ['js', 'css']);