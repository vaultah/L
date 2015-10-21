var gulp = require('gulp'),
    babel = require('gulp-babel'),
    uglify = require('gulp-uglify'),
    sourcemaps = require('gulp-sourcemaps'),
    uglify_inline = require('gulp-uglify-inline');

gulp.task('js', function() {
    return gulp.src(['public/assets/js/*.js'])
               // .pipe(sourcemaps.init())
               .pipe(babel())
               .pipe(uglify())
               // .pipe(sourcemaps.write())
               .pipe(gulp.dest('dist'));
});

gulp.task('html', function() {
    return gulp.src(['app/markup/**/*.html'])
               .pipe(uglify_inline())
               .pipe(gulp.dest('dist'))
});

gulp.task('default', ['js', 'html']);